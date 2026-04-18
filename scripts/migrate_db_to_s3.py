#!/usr/bin/env python3
"""
Migrate toot-id records from PostgreSQL to S3/Spaces.

Requires both DATABASE_* and S3_* env vars to be set.
Safe to re-run: existing objects are skipped.

Usage:
    pip install psycopg2-binary boto3
    python scripts/migrate_db_to_s3.py
"""
import os
import sys
from urllib.parse import urlparse

import boto3
import psycopg2
from botocore.exceptions import ClientError
from psycopg2.extras import RealDictCursor


def get_s3_key(url):
    parsed = urlparse(url)
    return f'.mastodon-meta/{parsed.path.lstrip("/")}'


def main():
    conn = psycopg2.connect(
        dbname=os.environ['DATABASE_NAME'],
        user=os.environ['DATABASE_USER'],
        password=os.environ['DATABASE_PASSWORD'],
        host=os.environ['DATABASE_HOST'],
        port=os.environ.get('DATABASE_PORT') or 5432,
        sslmode='require',
    )

    s3 = boto3.client(
        's3',
        endpoint_url=os.environ['S3_ENDPOINT'],
        aws_access_key_id=os.environ['S3_KEY'],
        aws_secret_access_key=os.environ['S3_SECRET'],
    )
    bucket = os.environ['S3_BUCKET']

    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT url, toot_id FROM posts WHERE toot_id IS NOT NULL ORDER BY id")
    rows = cur.fetchall()
    print(f"Found {len(rows)} rows to migrate")

    ok = skip = err = 0
    for row in rows:
        url, toot_id = row['url'], row['toot_id']
        key = get_s3_key(url)
        try:
            s3.head_object(Bucket=bucket, Key=key)
            print(f"  SKIP (exists) {key}")
            skip += 1
        except ClientError as e:
            if e.response['Error']['Code'] != '404':
                print(f"  ERROR {key}: {e}", file=sys.stderr)
                err += 1
                continue
            s3.put_object(Bucket=bucket, Key=key, Body=b'',
                          Metadata={'toot-id': str(toot_id)})
            print(f"  OK {key} → toot_id={toot_id}")
            ok += 1

    print(f"\nDone: {ok} written, {skip} skipped, {err} errors")
    conn.close()


if __name__ == '__main__':
    main()
