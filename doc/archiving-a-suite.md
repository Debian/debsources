# Archiving a suite

How to mark a suite as sticky (ensuring its packages remain around) *before* it
gets removed from the mirror network.

1) edit `lib/debsources/consts.py`, setting `archived: True` on the relevant suite
   (if it exists there otherwise, e.g., `*-lts` variants, don't bother)

2) on the DB: set to `t` the column `sticky` of the relevant suite, e.g.:

    ```sql
    update suites_info set sticky = 't' where name = 'squeeze';
    ```

3) archive the suite using the archiver `add` action, e.g.:

    ```shell
    bin/debsources-suite-archive add squeeze
    ```

or, more precisely on sources.d.o machine:

    ```shell
    sudo -u debsources PYTHONPATH=./lib bin/debsources-suite-archive add squeeze -vvv --single-transaction no
    ```

4) run `bin/debsources-suite-archive list` and check that the given suite is
   marked as both available and indexed, i.e., `True` on both columns
