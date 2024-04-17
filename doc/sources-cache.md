# cache/sources.txt - file format

The sources cache file, usually located in cache/sources.txt is an always
up-to-date cache of the sources currently available in a Debsources instance.
It is updated transactionally during Debsources update so, if you don't want to
interact with the Debsources database, you can use it for querying and quick
hacking on available source packages.

The format is as follows:

- one record per line; records are newline terminated

- each record is composed by multiple, tab-separated fields

- the fields are as follows:

  - **PACKAGE**: _source_ package name

  - **VERSION**: source package version

  - **AREA**: package archive area, one of `main`, `contrib`, `non-free`, `non-free-firmware`

  - **DSC**: absolute path to the corresponding `.dsc` file

    _note_: the fact that the path is absolute is unfortunate; in the future
    this might be changed to be a path relative to Debsources mirror dir
    (which is a configuration option)

  - **DEST**: absolute path to a directory where the source package is
    currently available in unpacked form (i.e. the dir that you will obtain by
    using `dpkg-source -x` on DSC)

    _note_: this might be changed in the future to be a path relative to
    Debsources sources dir (which is a configuration option)

  - **SUITES**: a comma separated list of Debian suites of which the source
    package is part. Suite names are alphabetically sorted.

# bin/debsources-foreach

The `bin/debsources-foreach` helper script can be used to quickly execute scripts in batch
on all available source packages, based on sources.txt content.

Here is an example which just dumps all information available in the source
cache, showing the augmented environment that foreach prepares for client code:

    $ bin/debsources-foreach cache/sources.txt 'echo ; pwd; env | grep DEBSOURCES_'

    /srv/debsources/sources/main/l/ledger/2.6.2-3.1
    DEBSOURCES_DIR=/srv/debsources/sources/main/l/ledger/2.6.2-3.1
    DEBSOURCES_PACKAGE=ledger
    DEBSOURCES_DSC=/srv/debsources/testdata/mirror/pool/main/l/ledger/ledger_2.6.2-3.1.dsc
    DEBSOURCES_AREA=main
    DEBSOURCES_VERSION=2.6.2-3.1
    DEBSOURCES_SUITES=jessie,wheezy,sid

    /srv/debsources/sources/contrib/n/nvidia-support/20131102+1
    DEBSOURCES_DIR=/srv/debsources/sources/contrib/n/nvidia-support/20131102+1
    DEBSOURCES_PACKAGE=nvidia-support
    DEBSOURCES_DSC=/srv/debsources/testdata/mirror/pool/contrib/n/nvidia-support/nvidia-support_20131102+1.dsc
    DEBSOURCES_AREA=contrib
    DEBSOURCES_VERSION=20131102+1
    DEBSOURCES_SUITES=jessie,sid

    [...]
