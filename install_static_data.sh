# this script installs all static files (patternfly, jquery, c3...)
# it expects that you have bower, git available

set -eox

bower install

# we have custom patches in c3:
#  * http://gitthub.com/c3js/c3/pull/1811
#  * http://gitthub.com/c3js/c3/pull/1812
curl -o bower_components/c3/c3.min.js https://raw.githubusercontent.com/TomasTomecek/c3/master/c3.min.js
