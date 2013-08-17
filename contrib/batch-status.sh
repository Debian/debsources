#!/bin/bash

LOGFILE="/srv/debsources/batch.log"
HOST="tytso.inria.fr"
TOTAL=40003

calc () {
    echo -e "scale=2\n$*" | bc
}

echo "Retrieving data from ${HOST}..."
started_at=$(ssh $HOST "head -n 1 $LOGFILE" | cut -f 1-2 -d' ')
pkg_count=$(ssh $HOST "grep ':DEBUG package' $LOGFILE" | wc -l)
last_line=$(ssh $HOST "tail -n 1 $LOGFILE")
last_time=$(echo $last_line | cut -f 1-2 -d' ')
last_log=$(echo $last_line | cut -f 5- -d' ')

now=$(date -u +%s)
percent_done=$(calc $pkg_count \* 100 / $TOTAL )
starttime_s=$(date -u -d "$started_at" +%s)
elapsed_s=$(calc $(date -u -d "$last_time" +%s) - $starttime_s )
elapsed_h=$(calc $elapsed_s / 60 / 60 )
speed_avg=$(echo -e "scale=2\n${pkg_count} / ${elapsed_s}" | bc)
est_duration_s=$(calc $elapsed_s \* 100 / $percent_done )
est_duration_h=$(calc $est_duration_s / 60 / 60 )
eta_s=$(calc $starttime_s + $est_duration_s )
eta=$(date -d @${eta_s})

echo
echo "Current status: ${last_log}"
echo "Status: ${percent_done}% completed (${pkg_count} packages) in ${elapsed_s} s (~${elapsed_h} hours)"
echo "Speed average: ${speed_avg} pkg/s"
echo "Estimated duration: ${est_duration_s} s (~${est_duration_h} hours)"
echo "ETA: ${eta}"
