
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
