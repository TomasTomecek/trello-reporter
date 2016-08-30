# so we can run test suite
set -ex
pgcont_server_start_local
psql -c "ALTER USER \"user\" CREATEDB;"
pgcont_server_stop
