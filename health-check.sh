#!/bin/bash

# Get the current Unix timestamp
current_time=$(date +%s)

# Get the Unix timestamp from the file
file_time=$(cat /tmp/health.log)

# Calculate the time difference in seconds
time_diff=$((current_time - file_time))

# Compare the time difference to 900 seconds (15 minutes)
if [ "$time_diff" -gt 900 ]; then
  # If the time difference is greater than 15 minutes, exit with error code 1
  echo "Last health check was more than 15 minutes ago."
  exit 1
else
  # Otherwise, exit with normal code 0
  exit 0
fi
