# lacof
[![License](https://img.shields.io/github/license/pawelad/lacof.svg)][license]
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)][black]
[![py.typed](https://img.shields.io/badge/py-typed-FFD43B)][pep561]

## Running locally
The easiest way run lacof locally is to install [Docker] and run:

```console
$ # Build Docker images
$ make docker-build
$ # Run Docker compose stack
$ make docker-run
```

If everything went well:
- API should be available at http://localhost:8000/api/v1/
- API docs should be available at http://localhost:8000/api/v1/docs
- [MinIO] Admin UI should be available at http://localhost:9001/
  (default credentials are `minioadmin:minioadmin`)

Alternatively, you can also run it without [Docker], but you need to have [PostgreSQL],
[Redis] and a [S3] compatible service (like [MinIO]) running locally:

```console
$ # Create a Python virtualenv
$ python3 -m venv venv
$ source venv/bin/activate
$ # Install dependencies
$ make install-dev
$ # Make sure PostgreSQL, Redis as S3 are avaible
$ docker compose up -d db minio redis
$ # Run the app
$ make run
```

### Migrations
If you're setting up the app for the first time (or some database model changes were
introduced since you last used it), you need to apply the database migrations:

```console
$ make docker-shell # Skip if not using Docker
$ make apply-migrations
```

It might also be useful to create a user for yourself with 
`PYTHONPATH=src python -m lacof.cli.create_user {user_name}`.

### Create a [MinIO] bucket
This [seems to be](https://github.com/minio/minio/issues/4769) the easiest way to
create a new bucket in [MinIO]:

```console
$ export MINIO_URL='http://minio:9000'
$ export MINIO_ACCESS_KEY='minioadmin'
$ export MINIO_SECRET_KEY='minioadmin'
$ export MINIO_BUCKET='lacof'
$ docker run --rm --network=lacof_default \
  -e MINIO_URL=MINIO_URL \
  -e MINIO_ACCESS_KEY=MINIO_ACCESS_KEY \
  -e MINIO_SECRET_KEY=MINIO_SECRET_KEY \
  -e MINIO_BUCKET=$MINIO_BUCKET \
  --entrypoint sh minio/mc -c "\
    /usr/bin/mc config host add myminio $MINIO_URL $MINIO_ACCESS_KEY $MINIO_SECRET_KEY && \
    /usr/bin/mc mb myminio/$MINIO_BUCKET \
  "
```

### Configuration
All configurable settings are loaded from environment variables and a local `.env`
file (in that order). Note that when running locally through [Docker], you need
to restart the app for it to pick up the changes.

Available settings:

```
# App environment
# Can be set to one of: 'production', 'local' or 'test'
ENVIRONMENT='local'

# Run app in debug mode (tracebacks are returned on errors)
# Docs: https://www.starlette.io/applications/#instantiating-the-application
DEBUG=True

# Database URL
# Docs: https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls
DATABASE_URL='postgresql+asyncpg://postgres@localhost/lacof'

# Test database URL
# Docs: https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls
DATABASE_URL='postgresql+asyncpg://postgres@localhost/lacof-test'

# Redis URL
# Docs: https://redis.readthedocs.io/en/stable/examples/connection_examples.html#Connecting-to-Redis-instances-by-specifying-a-URL-scheme.
REDIS_URL='redis://localhost:6379/0'

# AWS access key ID
AWS_ACCESS_KEY_ID='minioadmin'

# AWS secret access key
AWS_SECRET_ACCESS_KEY='minioadmin'

# S3 endpoint URL
# Needed for using MinIO instead of S3
S3_ENDPOINT_URL='http://localhost:9000'

# S3 bucket name
S3_BUCKET_NAME='lacof'

# Clip ML model name
# Avaible options: https://www.sbert.net/docs/sentence_transformer/pretrained_models.html#image-text-models
CLIP_MODEL_NAME='clip-ViT-B-32'

# Sentry DSN
# Docs: https://docs.sentry.io/platforms/python/configuration/options/
SENTRY_DSN='https://***@sentry.io/***'
```

## Makefile
Available `make` commands:

```console
$ make help
install                                   Install app dependencies
install-dev                               Install app dependencies (including dev)
pip-compile                               Compile requirements files
upgrade-package                           Upgrade a Python package (pass "package=<PACKAGE_NAME>")
upgrade-all                               Upgrade all Python packages
run                                       Run the app
create-migration                          Create an Alembic migration (pass "name=<MIGRATION_NAME>")
apply-migrations                          Apply Alembic migrations
format                                    Format code
test                                      Run the test suite
docker-build                              Build Docker compose stack
docker-run                                Run Docker compose stack
docker-stop                               Stop Docker compose stack
docker-shell                              Run bash inside dev container
clean                                     Clean dev artifacts
help                                      Show help message
```

## Authors
Developed and maintained by [Paweł Adamczak][pawelad].

Source code is available at [GitHub][github lacof].

Released under [Mozilla Public License 2.0][license].


[black]: https://github.com/psf/black
[docker]: https://www.docker.com/
[github lacof]: https://github.com/pawelad/lacof
[license]: ./LICENSE
[minio]: https://min.io/
[pawelad]: https://pawelad.me/
[pep561]: https://peps.python.org/pep-0561/
[postgresql]: https://www.postgresql.org/
[redis]: https://redis.io/
[s3]: https://aws.amazon.com/s3/
