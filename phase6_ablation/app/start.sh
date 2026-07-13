#!/bin/sh
sed -i "s/host='127\.0\.0\.1'/host='0.0.0.0'/g" /app/server.py
python /app/server.py
