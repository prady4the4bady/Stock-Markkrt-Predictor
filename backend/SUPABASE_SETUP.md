Supabase Setup (quick guide)

1) Create a Supabase project
   - Go to https://app.supabase.com and create a new project.
   - Note the Project URL and the Project's `anon` and `service_role` keys.

2) Database connection
   - In Project Settings > Database > Connection Pooling or Connection Info, copy the DB connection URL.
   - It will look like: postgres://user:password@dbhost:5432/postgres
   - Set this value as `DATABASE_URL` in your deployment environment (Render). Example:
     DATABASE_URL=postgresql+psycopg2://user:password@host:5432/dbname

3) Create the `predictions` table
   - In Supabase Dashboard → SQL Editor, run the SQL script in `backend/sql/create_supabase_table.sql`.

4) Configure environment variables for the backend (Render)
   - Add/Update these env vars in Render service settings:
     - DATABASE_URL (Supabase Postgres URL)
     - SECRET_KEY (your JWT secret)
     - SUPABASE_URL (optional, if using Supabase REST or Storage)
     - SUPABASE_SERVICE_ROLE_KEY (optional, for server-side operations)

5) Update Vercel (frontend)
   - Set `VITE_API_URL` to your Render backend primary URL (e.g., https://nexustrader-api.onrender.com)

6) Verify
   - Deploy backend on Render and confirm `/api/version` responds.
   - From the backend, you can write to the `predictions` table using the provided `DATABASE_URL`.

If you want, I can:
- Apply the `DATABASE_URL` change to `database.py` (done) and push a commit, and
- Create the Supabase table for you if you provide the database URL or a SQL runner key, or instruct you how to run the SQL in the Supabase SQL editor.
