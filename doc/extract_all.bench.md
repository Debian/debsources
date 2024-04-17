# first extraction

zack@tytso:/srv/source.debian.org$ time bin/extract_all
real 111m46.898s
user 74m26.915s
sys 19m7.196s

# one (random) update after mirror pulse

zack@tytso:/srv/source.debian.org$ time bin/extract_all
real 3m52.108s
user 0m51.531s
sys 0m29.690s

# a do-nothing update

zack@tytso:/srv/source.debian.org$ time bin/extract_all
real 2m55.179s
user 0m10.025s
sys 0m15.985s

# clean up bench

zack@tytso:/srv/sources.debian.org$ time rm -rf sources/
real 3m7.814s
user 0m5.996s
sys 2m27.109s
