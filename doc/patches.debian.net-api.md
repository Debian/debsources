Navigation
================

By prefix
----------

* /api/prefix/PREFIX/
Retrieve the packages under a prefix

By list
----------

* /list/INT/
Retrieve a list of paginated packages.
INT is an integer to indicate the page number


Package Summary API
================

The package summary API allows the user to retrieve patch related information 
providing:

* a package, version


URL schema
----------

* /patches/api/summary/PACKAGE/VERSION/
  * Version can be a suite alias (jessie), a package version or the keyword
  "latest"


JSON structure
---------------

The API returns the package related information such as the package, the 
version, the format, a checksum of the orig.tar.gz as well as list of patches applied in the package along with some other useful information such as the 
file deltas, the description and the download url.

The above information are to be inserted in the following JSON structure

{
    results:
        {
            package: "----",
            version: "----",
            format: "----",
            orig_checksum: "----",
            patches: [
                {
                    name: "----",
                    url: "----"
                },
                {
                    name: "----",
                    url: "----"
                },
                {
                    name: "----",
                    url: "----"
                },
            ]
        },
}

Patch API
================

This API allows the user to retrieve details of a single patch

URL schema
----------

* /patches/api/patch/PACKAGE/VERSION/PATCH_PATH

The PATCH_PATH is the path of the patch __inside__ the debian/patches folder.
Version can be a suite alias (jessie), a package version or the keyword 
"latest"

JSON structure
---------------

The results are homogeneous, with the package summary API. 

{
    results:
        {
            package: "----",
            version: "----",
            format: "----",
            orig_checksum: "----",
            name: "----",
            file_deltas: "----",
            description: "----",
            url: "----"
        }
}

The JSON structure is identical to the summary package one with the results
field. This enables the user to parse the API with a single tool.
