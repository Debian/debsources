Debsources has the ability to exclude parts of the available content from
processing. Exclusions come in 2 flavors:

- file-based exclusions
- package exclusions

# File-based exclusions

A file called `LOCAL/exclude.conf`, where `LOCAL` is Debsources local directory
(`local_dir` configuration entry), can be used to exclude specific files from
Debsources operations.

Files are excluded just after extraction, removed from the DB, and not further
processed by any plugin.

The file is a Deb822-like file made of several stanzas (or "paragraphs"),
separated by empty lines. The general stanza format is as follows:

    Explanation: (optional) some commentary explaining the exclusion
    Package: affected source package
    Files: UNIX-style glob of files to exclude
    Action: remove

`Files` field is space separated. All fields are "folded", i.e. they can be
broken into several physical lines, indenting subsequent lines by one space.

`Package` and `Files` concur to identify the files to be excluded, as follows:

- initially, all files of (any version of) `Package` are eligible for exclusion

- eligible files are filtered using `Files`: only files that match at least one
  of its glob patterns are retained. Patterns are matched relatively to
  package root directories, AKA their extraction directories

After the evaluation of the above fields, all files eligible for exclusion get
excluded, executing the given `Action`.

Supported actions, i.e., valid fields for `Action` are:

- `remove`: remove excluded files from both the package extraction directory
  and Debsources DB.

## Maintenance

Note that changes to `exclude.conf` do not trigger re-extraction of a package.
If you change `exclude.conf` to exclude a file, you will need to remove the
package from debsources and update again to have the exclusion take effect;
similarly if you drop a previously enacted exclusion.

## Examples

    Explanation: #742605
    Package: chromium-browser
    Files: foo/bar.c
    Action: remove

    Explanation: non free, non redistributable, see #XXXXXX
    Package: bad-bad-package
    Files: baz/qux/*/*.c
    Action: remove

# Package exclusions

The configuration file is shared with file-based exclusions
(`LOCAL/exclude.conf`), and will therefore contain entries for both file-based
and package exclusions. To decide which is which, the following rule applies.
A stanza that contains a `Files:` field is a file-based exclusion stanza. A
stanza that does _not_ contain a `Files:` (and contains a `Package:` field) is
a package exclusion stanza.

The general stanza format for package exclusions is as follows:

    Explanation: (optional) some commentary explaining the exclusion
    Package: affected source package
    Version: (optional) affected package version
    Action: ignore

The fields `Explanation`, `Package`, and `Action` are as per file-based
exclusions (although `Action` supports different values, see below).

To be excluded, the name of a given source package must match the `Package`
field of at least one package exclusion stanza. If the stanza does not have a
`Version` field, then the package is excluded.

If the `Version` field is present, it must be a single (source) package
version, as per Debian Policy. If a package matches the `Package` field of a
stanza that also has a `Version` field, then it is excluded if and only if its
version matches the value of that field.

Supported actions, i.e., valid fields for `Action` are:

- `ignore`: ignore the package when updating Debsources. At present, this
  specifically means only not _adding_ it to the data storage, but not
  necessarily removing it if it has been added in the past.
