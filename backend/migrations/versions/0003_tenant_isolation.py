
'''PostgreSQL tenant isolation ? read policy implementation.'''

revision = "0003_tenant_isolation"
down_revision = "0002_database_security"
branch_labels = None
depends_on = None


def install_read_policies(bind):

    if bind.dialect.name != "postgresql":
        raise RuntimeError("PostgreSQL required")

    execute = bind.exec_driver_sql

    execute("CREATE SCHEMA sentinel_security")

    execute(
        "REVOKE ALL ON SCHEMA sentinel_security FROM PUBLIC"
    )

    execute(
        "GRANT USAGE ON SCHEMA sentinel_security TO sentinel_app"
    )

    execute(
        "GRANT USAGE ON SCHEMA public TO sentinel_app"
    )

    functions = [
        (
            "current_user_id", "", "text",
            '''
            SELECT NULLIF(
                current_setting('sentinel.user_id', true),
                ''
            )
            '''
        ),
        (
            "current_app_role", "", "text",
            '''
            SELECT CAST(u.role AS text)
            FROM public.users u
            WHERE u.id = sentinel_security.current_user_id()
            AND u.active
            AND u.role IN ('admin', 'analyst', 'officer')
            '''
        ),
        (
            "can_read_project", "pid text", "boolean",
            '''
            SELECT EXISTS (
                SELECT 1
                FROM public.projects p
                WHERE p.id = pid
                AND sentinel_security.current_app_role()
                    IS NOT NULL
                AND (
                    sentinel_security.current_app_role() = 'admin'
                    OR p.owner_id =
                        sentinel_security.current_user_id()
                    OR EXISTS (
                        SELECT 1
                        FROM public.project_access pa
                        WHERE pa.project_id = p.id
                        AND pa.user_id =
                            sentinel_security.current_user_id()
                    )
                )
            )
            '''
        ),
        (
            "can_manage_project", "pid text", "boolean",
            '''
            SELECT EXISTS (
                SELECT 1
                FROM public.projects p
                WHERE p.id = pid
                AND (
                    sentinel_security.current_app_role() = 'admin'
                    OR (
                        sentinel_security.current_app_role()
                            = 'analyst'
                        AND p.owner_id =
                            sentinel_security.current_user_id()
                    )
                )
            )
            '''
        ),
        (
            "can_read_investigation", "iid text", "boolean",
            '''
            SELECT EXISTS (
                SELECT 1
                FROM public.investigations i
                WHERE i.id = iid
                AND sentinel_security.can_read_project(
                    i.project_id
                )
                AND (
                    sentinel_security.current_app_role()
                        IN ('admin', 'analyst')
                    OR (
                        sentinel_security.current_app_role()
                            = 'officer'
                        AND i.assigned_to_id =
                            sentinel_security.current_user_id()
                    )
                )
            )
            '''
        ),
    ]

    for name, args, returns, body in functions:

        execute(f'''
            CREATE FUNCTION sentinel_security.{name}({args})
            RETURNS {returns}
            LANGUAGE SQL
            STABLE
            SECURITY DEFINER
            SET search_path = pg_catalog, pg_temp
            AS $$ {body} $$
        ''')

        signature = "text" if args else ""

        execute(
            f"REVOKE ALL ON FUNCTION "
            f"sentinel_security.{name}({signature}) "
            "FROM PUBLIC"
        )

        execute(
            f"GRANT EXECUTE ON FUNCTION "
            f"sentinel_security.{name}({signature}) "
            "TO sentinel_app"
        )

    policies = {
        "users": '''
            id = sentinel_security.current_user_id()
            AND active
        ''',
        "projects": '''
            sentinel_security.can_read_project(id)
        ''',
        "project_access": '''
            (
                user_id = sentinel_security.current_user_id()
                AND sentinel_security.current_app_role()
                    IS NOT NULL
            )
            OR sentinel_security.can_manage_project(project_id)
        ''',
        "imagery": '''
            sentinel_security.can_read_project(project_id)
        ''',
        "analyses": '''
            sentinel_security.can_read_project(project_id)
        ''',
        "candidate_regions": '''
            EXISTS (
                SELECT 1 FROM public.analyses a
                WHERE a.id = candidate_regions.analysis_id
                AND sentinel_security.can_read_project(a.project_id)
            )
        ''',
        "investigations": '''
            sentinel_security.can_read_investigation(id)
        ''',
        "analyst_decisions": '''
            sentinel_security.can_read_investigation(
                investigation_id
            )
        ''',
        "reports": '''
            EXISTS (
                SELECT 1 FROM public.analyses a
                WHERE a.id = reports.analysis_id
                AND sentinel_security.can_manage_project(a.project_id)
            )
        ''',
    }

    for table, condition in policies.items():

        execute(
            f"ALTER TABLE public.{table} "
            "ENABLE ROW LEVEL SECURITY"
        )

        execute(
            f"REVOKE ALL ON TABLE public.{table} "
            "FROM PUBLIC, sentinel_app"
        )

        if table == "users":
            execute(
                "GRANT SELECT (id, email, role, active) "
                "ON public.users TO sentinel_app"
            )
        else:
            execute(
                f"GRANT SELECT ON public.{table} "
                "TO sentinel_app"
            )

        execute(f'''
            CREATE POLICY tenant_read
            ON public.{table}
            FOR SELECT
            TO sentinel_app
            USING ({condition})
        ''')




def install_auth_functions(bind):

    execute = bind.exec_driver_sql

    execute('''
        CREATE FUNCTION sentinel_security.register_officer(
            p_id text,
            p_email text,
            p_hash text
        )
        RETURNS text
        LANGUAGE SQL
        VOLATILE
        SECURITY DEFINER
        SET search_path = pg_catalog, pg_temp
        AS $$
            INSERT INTO public.users AS u
            (
                id, email, password_hash,
                role, active, created_at
            )
            SELECT
                p_id, lower(p_email), p_hash,
                'officer', true, CURRENT_TIMESTAMP
            WHERE
                sentinel_security.current_user_id() IS NULL
                AND length(p_id) BETWEEN 1 AND 36
                AND length(p_email) BETWEEN 1 AND 320
                AND p_hash LIKE 'pbkdf2_sha256$%'
            ON CONFLICT (email) DO NOTHING
            RETURNING u.id::text
        $$
    ''')

    execute('''
        CREATE FUNCTION sentinel_security.login_lookup(
            p_email text
        )
        RETURNS TABLE (
            id text,
            password_hash text,
            active boolean
        )
        LANGUAGE SQL
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, pg_temp
        AS $$
            SELECT
                u.id::text,
                u.password_hash,
                u.active
            FROM public.users u
            WHERE u.email = lower(p_email)
            AND u.active
            AND sentinel_security.current_user_id() IS NULL
        $$
    ''')

    execute('''
        CREATE FUNCTION sentinel_security.eligible_user(
            p_project text,
            p_user text
        )
        RETURNS TABLE (
            id text,
            role text,
            active boolean
        )
        LANGUAGE SQL
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, pg_temp
        AS $$
            SELECT
                u.id::text,
                u.role::text,
                u.active
            FROM public.users u
            WHERE u.id = p_user
            AND u.active
            AND u.role IN ('analyst', 'officer')
            AND sentinel_security.can_manage_project(
                p_project
            )
        $$
    ''')

    signatures = (
        "register_officer(text, text, text)",
        "login_lookup(text)",
        "eligible_user(text, text)",
    )

    for signature in signatures:

        execute(
            "REVOKE ALL ON FUNCTION "
            f"sentinel_security.{signature} FROM PUBLIC"
        )

        execute(
            "GRANT EXECUTE ON FUNCTION "
            f"sentinel_security.{signature} TO sentinel_app"
        )




def install_write_policies(bind):

    run = bind.exec_driver_sql

    uid = "sentinel_security.current_user_id()"
    role = "sentinel_security.current_app_role()"

    def manage(pid):
        return f"sentinel_security.can_manage_project({pid})"

    def read(pid):
        return f"sentinel_security.can_read_project({pid})"

    def grant(table, privileges):
        run(
            f"GRANT {privileges} ON public.{table} "
            "TO sentinel_app"
        )

    def policy(table, action, using=None, check=None):
        sql = (
            f"CREATE POLICY tenant_{action.lower()} "
            f"ON public.{table} FOR {action} TO sentinel_app"
        )
        if using is not None:
            sql += f" USING ({using})"
        if check is not None:
            sql += f" WITH CHECK ({check})"
        run(sql)

    run(f'''
        ALTER POLICY tenant_read ON public.projects
        USING (
            {role} IS NOT NULL AND (
                {role} = 'admin'
                OR owner_id = {uid}
                OR EXISTS (
                    SELECT 1 FROM public.project_access pa
                    WHERE pa.project_id = projects.id
                    AND pa.user_id = {uid}
                )
            )
        )
    ''')

    grant("projects", "INSERT, DELETE, UPDATE (name, description)")

    policy("projects", "INSERT", check=f'''
        {role} IN ('admin', 'analyst')
        AND owner_id = {uid}
    ''')

    owner = f'''
        {role} = 'admin'
        OR ({role} = 'analyst' AND owner_id = {uid})
    '''

    policy("projects", "UPDATE", owner, owner)
    policy("projects", "DELETE", owner)

    grant("project_access", "INSERT, DELETE, UPDATE (id)")

    manager = manage("project_id")

    policy("project_access", "INSERT", check=f'''
        {manager}
        AND EXISTS (
            SELECT 1
            FROM sentinel_security.eligible_user(project_id, user_id)
        )
        AND NOT EXISTS (
            SELECT 1 FROM public.projects p
            WHERE p.id = project_access.project_id
            AND p.owner_id = project_access.user_id
        )
    ''')

    policy("project_access", "UPDATE", manager, "false")

    policy("project_access", "DELETE", using=f'''
        {manager}
        AND NOT EXISTS (
            SELECT 1 FROM public.investigations i
            WHERE i.project_id = project_access.project_id
            AND i.assigned_to_id = project_access.user_id
        )
    ''')

    grant("imagery", "INSERT")

    policy("imagery", "INSERT", check=f'''
        {manager}
        OR (
            {role} = 'analyst'
            AND {read('project_id')}
            AND (
                metadata_json IS NULL
                OR metadata_json::text = 'null'
            )
            AND crs IS NULL
        )
    ''')

    grant("analyses", "INSERT")
    grant("analyses", "UPDATE (status, parameters_json, results_json)")

    policy("analyses", "INSERT", check=f'''
        {manager}
        AND status = 'pending'
        AND before_imagery_id <> after_imagery_id
        AND EXISTS (
            SELECT 1 FROM public.imagery im
            WHERE im.id = analyses.before_imagery_id
            AND im.project_id = analyses.project_id
        )
        AND EXISTS (
            SELECT 1 FROM public.imagery im
            WHERE im.id = analyses.after_imagery_id
            AND im.project_id = analyses.project_id
        )
    ''')

    policy(
        "analyses", "UPDATE",
        f"{manager} AND status = 'pending'",
        f"{manager} AND status = 'completed'"
    )

    grant("candidate_regions", "INSERT")

    policy("candidate_regions", "INSERT", check=f'''
        EXISTS (
            SELECT 1 FROM public.analyses a
            WHERE a.id = candidate_regions.analysis_id
            AND {manage('a.project_id')}
            AND a.status = 'completed'
        )
    ''')

    run(f'''
        ALTER POLICY tenant_read ON public.investigations
        USING (
            {read('project_id')}
            AND (
                {role} IN ('admin', 'analyst')
                OR ({role} = 'officer' AND assigned_to_id = {uid})
            )
        )
    ''')

    grant("investigations", "INSERT")
    grant("investigations", "UPDATE (assigned_to_id, status)")

    policy("investigations", "INSERT", check=f'''
        {manager}
        AND assigned_to_id IS NULL
        AND status = 'open'
        AND EXISTS (
            SELECT 1 FROM public.candidate_regions r
            JOIN public.analyses a ON a.id = r.analysis_id
            WHERE r.id = investigations.region_id
            AND a.project_id = investigations.project_id
            AND a.status = 'completed'
        )
    ''')

    allowed = f'''
        {manager}
        OR (
            {role} = 'officer'
            AND assigned_to_id = {uid}
            AND {read('project_id')}
        )
    '''

    policy("investigations", "UPDATE", allowed, allowed)

    run(f'''
        CREATE FUNCTION sentinel_security.guard_investigation()
        RETURNS trigger
        LANGUAGE plpgsql
        SET search_path = pg_catalog, pg_temp
        AS $$
        BEGIN
            IF {role} = 'officer' THEN
                IF NEW.assigned_to_id IS DISTINCT FROM OLD.assigned_to_id
                   OR NOT (
                       (OLD.status = 'open' AND NEW.status = 'in_progress')
                       OR
                       (OLD.status = 'in_progress' AND NEW.status = 'submitted')
                   )
                THEN
                    RAISE EXCEPTION 'Invalid officer operation'
                    USING ERRCODE = '42501';
                END IF;

            ELSIF {manage('OLD.project_id')} THEN
                IF NEW.assigned_to_id IS DISTINCT FROM OLD.assigned_to_id
                THEN
                    IF OLD.status <> 'open'
                       OR NEW.status <> OLD.status
                       OR NOT EXISTS (
                           SELECT 1
                           FROM sentinel_security.eligible_user(
                               OLD.project_id, NEW.assigned_to_id
                           ) u
                           WHERE u.role = 'officer'
                       )
                       OR NOT EXISTS (
                           SELECT 1 FROM public.project_access pa
                           WHERE pa.project_id = OLD.project_id
                           AND pa.user_id = NEW.assigned_to_id
                       )
                    THEN
                        RAISE EXCEPTION 'Invalid assignment'
                        USING ERRCODE = '42501';
                    END IF;

                ELSIF NEW.status IS DISTINCT FROM OLD.status
                      AND NOT (
                          OLD.status = 'submitted'
                          AND NEW.status = 'reviewed'
                      )
                THEN
                    RAISE EXCEPTION 'Invalid review transition'
                    USING ERRCODE = '42501';
                END IF;

            ELSE
                RAISE EXCEPTION 'Update denied'
                USING ERRCODE = '42501';
            END IF;

            RETURN NEW;
        END;
        $$
    ''')

    run('''
        REVOKE ALL ON FUNCTION
        sentinel_security.guard_investigation()
        FROM PUBLIC
    ''')

    run('''
        CREATE TRIGGER guard_investigation
        BEFORE UPDATE ON public.investigations
        FOR EACH ROW EXECUTE FUNCTION
        sentinel_security.guard_investigation()
    ''')

    grant("analyst_decisions", "INSERT")

    run('''
        ALTER TABLE public.analyst_decisions
        ADD CONSTRAINT uq_investigation_decision
        UNIQUE (investigation_id)
    ''')

    policy("analyst_decisions", "INSERT", check=f'''
        reviewer_id = {uid}
        AND decision IN ('confirmed', 'rejected', 'inconclusive')
        AND EXISTS (
            SELECT 1 FROM public.investigations i
            WHERE i.id = analyst_decisions.investigation_id
            AND {manage('i.project_id')}
            AND i.status IN ('submitted', 'reviewed')
        )
    ''')



    run('''
        CREATE FUNCTION sentinel_security.check_review_consistency()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, pg_temp
        AS $$
        DECLARE
            iid text;
            final_status text;
            has_decision boolean;
        BEGIN
            IF TG_TABLE_NAME = 'investigations' THEN
                iid := NEW.id;
            ELSE
                iid := NEW.investigation_id;
            END IF;

            SELECT i.status INTO final_status
            FROM public.investigations i
            WHERE i.id = iid;

            SELECT EXISTS (
                SELECT 1 FROM public.analyst_decisions d
                WHERE d.investigation_id = iid
            ) INTO has_decision;

            IF (final_status = 'reviewed')
                IS DISTINCT FROM has_decision
            THEN
                RAISE EXCEPTION 'Review and decision must agree'
                USING ERRCODE = '23514';
            END IF;

            RETURN NULL;
        END;
        $$
    ''')

    run('''
        REVOKE ALL ON FUNCTION
        sentinel_security.check_review_consistency()
        FROM PUBLIC
    ''')

    run('''
        CREATE CONSTRAINT TRIGGER investigation_review_consistency
        AFTER INSERT OR UPDATE ON public.investigations
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION
        sentinel_security.check_review_consistency()
    ''')

    run('''
        CREATE CONSTRAINT TRIGGER decision_review_consistency
        AFTER INSERT ON public.analyst_decisions
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION
        sentinel_security.check_review_consistency()
    ''')



def upgrade():
    from alembic import op
    from sqlalchemy import text

    bind = op.get_bind()

    if bind.dialect.name == "sqlite":
        return

    if bind.dialect.name != "postgresql":
        raise RuntimeError("PostgreSQL required")

    has_postgis = bind.scalar(text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_extension
            WHERE extname = 'postgis'
        )
    """))

    if not has_postgis:
        raise RuntimeError("PostGIS extension required")

    flags = bind.execute(text("""
        SELECT rolcanlogin, rolsuper, rolbypassrls,
               rolcreatedb, rolcreaterole,
               rolinherit, rolreplication
        FROM pg_roles
        WHERE rolname = 'sentinel_app'
    """)).one_or_none()

    if flags is None or any(flags):
        raise RuntimeError(
            "Missing or unsafe sentinel_app role"
        )

    memberships = bind.scalar(text("""
        SELECT count(*)
        FROM pg_auth_members
        WHERE member = (
            SELECT oid FROM pg_roles
            WHERE rolname = 'sentinel_app'
        )
    """))

    if memberships:
        raise RuntimeError("Unsafe runtime role membership")

    owned_tables = bind.scalar(text("""
        SELECT count(*)
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
        AND c.relname IN (
            'users', 'projects', 'project_access',
            'imagery', 'analyses', 'candidate_regions',
            'investigations', 'analyst_decisions',
            'reports'
        )
        AND c.relowner = (
            SELECT oid FROM pg_roles
            WHERE rolname = current_user
        )
        AND NOT c.relforcerowsecurity
    """))

    if owned_tables != 9:
        raise RuntimeError(
            "Migration ownership validation failed"
        )

    install_read_policies(bind)
    install_auth_functions(bind)
    install_write_policies(bind)


def downgrade():
    raise RuntimeError(
        "Manual security review required."
    )
