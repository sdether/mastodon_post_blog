Mastodon Post Blog
==================

Service that creates a Mastodon toot for each new blog post and returns the toot ID so the
blog can render a comment thread. Supports three deployment targets from a single codebase:

- **DigitalOcean Functions** — `packages/postblog/post/__main__.py` (`main`)
- **AWS Lambda** — `packages/postblog/post/__main__.py` (`handler`)
- **Docker / Flask** — `packages/postblog/post/app.py`

## Environment Variables

| Variable               | Description                                                                                                                                            |
|------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| `MASTODON_HOST`        | Mastodon instance hostname (assumed `https://`). Returned to callers to construct links.                                                               |
| `MASTODON_USER`        | Mastodon user under which toots are created. Returned to callers.                                                                                      |
| `MASTODON_OAUTH_TOKEN` | OAuth token authorising the service to post on behalf of the user.                                                                                     |
| `BLOG_POST_PATTERN`    | Regex that identifies blog post URLs, e.g. `^https://claassen.net/geek/blog/\d+/\d+/[^/]+`                                                             |
| `BLOG_POST_POSTFIX`    | Text appended to every toot, e.g. `#blog #iloggable`                                                                                                   |
| `BLOG_TITLE_PATTERN`   | Regex with a named `title` group to extract the post title from `og:title`. Useful when the site name is included, e.g. `^(?P<title>.*?)( - claassen\.net)$` |
| `S3_BUCKET`            | Bucket used to store toot-id metadata.                                                                                                                 |
| `S3_ENDPOINT`          | Full endpoint URL for S3, e.g. `https://sfo3.digitaloceanspaces.com`. Omit for standard AWS S3.                                                        |
| `S3_KEY` / `S3_SECRET` | S3 access key pair. Omit on AWS Lambda when using an IAM execution role.                                                                               |

## Mastodon Status Formatting

Mastodon status updates are constructed from this template:

```
{title}

[{description}]
[{BLOG_POST_POSTFIX}]
[{tags}]
{url}
```

where:
- `title` - `mastodon:title` meta header if present, otherwise `og:title` or `twitter:description` processed by `BLOG_TITLE_PATTERN`
- `description` - `mastodon:description` or `og:description` or `twitter:description`
- `tags` - `mastodon:tags`. expects a free form string


## S3 / Spaces Storage Setup

Toot IDs are stored as zero-byte objects with metadata in an S3-compatible bucket. No schema
or initialisation is needed — objects are created on demand.

1. Create a private bucket (objects are never served publicly).
2. For DO Spaces: generate a Spaces key in **API → Spaces Keys → Generate New Key**.
3. For AWS S3: create a bucket and either create an IAM user with `s3:GetObject`/`s3:PutObject`/`s3:HeadObject` permissions, or attach those permissions to the Lambda execution role.

## Deployment

### DigitalOcean Functions

Environment variables are read from your shell at deploy time via the `${VAR}` references in
`project.yml`. Put your secrets in a file (already gitignored) and source it before deploying:

```shell
# prod.env (gitignored) — never commit this file
MASTODON_USER=...
MASTODON_HOST=...
MASTODON_OAUTH_TOKEN=...
BLOG_POST_PATTERN=...
BLOG_POST_POSTFIX=...
BLOG_TITLE_PATTERN=...
S3_KEY=...
S3_SECRET=...
S3_ENDPOINT=https://sfo3.digitaloceanspaces.com
S3_BUCKET=...
```

```shell
# One-time setup
doctl auth init
doctl serverless install
doctl serverless connect <namespace> --access-key <dof_v1_key_id:secret>

# Deploy (source secrets first so project.yml ${VAR} references resolve)
source prod.env
doctl serverless deploy . --remote-build

# Get the function URL
doctl serverless functions get postblog/post --url

# Test
doctl serverless functions invoke postblog/post --param url:https://yourblog.com/your-post/
```

Replace `{postblog_location}` in `javascript/mastodon-loader.js` with the returned URL.

### AWS Lambda

1. Create a Lambda function (Python 3.11 runtime).
2. Set the handler to `__main__.handler`.
3. Zip `packages/postblog/post/` (including `requirements.txt` dependencies) and upload, or use a
   deployment tool such as AWS SAM or CDK.
4. Attach an IAM execution role with `s3:GetObject`, `s3:PutObject`, and `s3:HeadObject` on the
   target bucket — then `S3_KEY`, `S3_SECRET`, and `S3_ENDPOINT` can all be omitted.
5. Wire the function to an API Gateway HTTP API (proxy integration). The function returns the
   standard `{statusCode, headers, body}` shape that API Gateway expects.
6. Set all remaining environment variables in the Lambda configuration.

### Docker / Flask

```shell
docker build . -t postblog
docker-compose up
```

The service listens on port 8000. For local development with live reload, the `docker-compose.yaml`
volume-mounts the repository so edits to `packages/postblog/post/` take effect without a rebuild.

### Local CLI (no server)

```shell
# Set env vars, then:
python packages/postblog/post/__main__.py https://yourblog.com/your-post/
```

## Migration from PostgreSQL

If migrating from the previous database-backed version, use `scripts/migrate_db_to_s3.py` to seed the
bucket from the existing `posts` table:

```shell
pip install psycopg2-binary boto3

# Set both DATABASE_* and S3_* env vars, then:
python scripts/migrate_db_to_s3.py
```

The script skips objects that already exist and is safe to re-run.

## Background / Prior Art

- https://claassen.net/geek/blog/2024/02/mastodon-integration.html — original Lambda integration
- https://claassen.net/geek/blog/2024/08/mastodon-integration-revisited.html — migration to Flask/ECS
