# DESIGN FRAGMENT ONLY: inside an EXISTING owner-gated native-app proxy location.
# This fragment creates no app/API routes and has no upstream or credentials.
# Check that the upstream sends uncompressed HTML with one closing head marker.
# Preserve the existing auth, Host checks, API/method restrictions and headers.
proxy_set_header Accept-Encoding "";
sub_filter_once on;
# Default eligible MIME is text/html. Do not widen this to JavaScript or JSON.
sub_filter '</head>' '<link rel="stylesheet" href="/__outlands/theme/netwall.css"></head>';
