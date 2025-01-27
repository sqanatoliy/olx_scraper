#!/bin/bash

set -e

host="$1"
shift
cmd="$@"

until pg_isready -h "$host" -p 5432 -q; do
  >&2 echo "Postgres is unavailable - sleeping"
  sleep 2
done

>&2 echo "Postgres is up - executing command"
exec $cmd