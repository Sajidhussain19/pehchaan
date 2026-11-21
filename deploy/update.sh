#!/usr/bin/env bash
# deploy/update.sh — update the running Pehchaan server after a `git push` (run ON the EC2 server).
#
# WHAT: pulls the latest code, rebuilds the Docker image, and replaces the running container.
#       Reminders and learned preferences live in the "pehchaan-state" volume, so they are kept.
# WHY:  One command instead of five, so an update just before the demo can't go half-done.
set -euo pipefail                                   # stop at the first error
cd "$(dirname "$0")/.."
git pull --ff-only
docker build -t pehchaan .
sudo docker rm -f pehchaan 2>/dev/null || true
sudo docker run -d --name pehchaan --restart unless-stopped \
  -p 8000:8000 --env-file /etc/pehchaan.env -v pehchaan-state:/app/state pehchaan
sleep 3
curl -fsS localhost:8000/health && echo "  <- Pehchaan is up"
