
umask 0002

verbose="1"

info() {
    local msg="$1"
    if [ "$verbose" = "1" ] ; then
	echo "I: $msg"
    fi
}

warn() {
    local msg="$1"
    echo "W: $msg"
}

err() {
    local msg="$1"
    local code="$2"
    echo "E: $msg"
    exit $code
}


stats_period=1000
stats_label=""
stats_total=""
stats_count=""

stats_init() {
    stats_label="$1"
    stats_total="$2"
    stats_count=0
}

stats_print() {
    if [ "$verbose" = "1" ] ; then
	msg="heartbeat: $stats_count"
	if [ -n "$stats_total" ] ; then
	    msg="$msg / $stats_total"
	fi
        info "$msg"
    fi
}

stats_tick() {
    stats_count=$[$stats_count+1]
    if [ $[$stats_count % $stats_period] -eq 0 ] ; then
        stats_print
    fi
}
