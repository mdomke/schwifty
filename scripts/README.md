# schwifty registry update

The generated registries in `schwifty/bank_registry`, `schwifty/scl_registry` and
`schwifty/iban_registry` are built from official sources by the scripts in this directory.

## Automated updates

The [`update-registries`](../.github/workflows/update-registries.yml) workflow runs every Monday.
It updates every source in its own job and proposes all changes in one pull request from the
`registry-update` branch. The pull request lists what changed per registry: added, retired and
renamed bank codes, new BICs and changed checksum methods. A source that fails opens an issue
titled "Registry source broken: <source>". The issue is closed after the next successful update.

You can also run the workflow by hand from the Actions tab, for some sources only, or with
`force` to keep changes that fail the sanity checks below.

## Manual updates

Run the update from the root directory. The dependencies of the scripts are in the `scripts`
dependency group, which the task installs:

    $ uv run poe update-registries          # all sources that can be downloaded automatically
    $ uv run poe update-registries de scl   # only some of them
    $ uv run poe registry-diff              # summarize the changes since HEAD

A source that fails doesn't stop the others. After each source, its changes are checked, and they
are reverted if

* an entry is invalid, e.g. a bank code without a name or an invalid BIC,
* more than 5% of the active bank codes (but at least 5) are retired or dropped at once, which
  usually means that the source is incomplete, or
* more than 5% of the BICs of the SCL directory, or a country of the IBAN registry, disappear.

Pass `--force` to keep such changes when they are expected. Checksum methods that the registry
uses but schwifty doesn't implement are reported as warnings.

Lithuania and the IBAN registry are not updated automatically, because lb.lt and swift.com reject
automated downloads. Download the file in a browser and pass it to the script:

    $ uv run --group scripts python -m scripts.get_bank_registry_lt branches.xml
    $ uv run --group scripts python -m scripts.get_iban_registry iban-registry.txt
