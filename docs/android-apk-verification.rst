Android APK verification
========================

Starting with version ``0.2.0``, PythonHere Android APKs are distributed through
GitHub Releases as the central distribution channel and are signed with the
PythonHere Android signing certificate.

PythonHere uses several release verification measures to help users confirm that
a downloaded APK is authentic:

* APKs are built by this repository's GitHub Actions workflow.
* Build provenance is published as GitHub `artifact attestations <https://github.com/b3b/pythonhere/attestations>`_.
* Published releases are protected by GitHub immutable releases.
* APKs are signed with the PythonHere Android signing certificate.

Before installing a downloaded APK, you can verify its provenance, release
integrity, and Android signing certificate using the checks below.

Download the APK
----------------

Download the APK from the PythonHere Releases page:

https://github.com/b3b/pythonhere/releases

In the commands below, replace ``<version>`` with the release tag you
downloaded, for example ``0.2.0``.

Verify GitHub Actions provenance
--------------------------------

Use the GitHub CLI to verify that the downloaded APK was built by this
repository's GitHub Actions workflow::

    gh attestation verify pythonhere-*.apk -R b3b/pythonhere

This verifies the APK's build provenance and confirms that the artifact is
associated with the ``b3b/pythonhere`` repository.

Verify the downloaded release asset
-----------------------------------

Verify that the downloaded APK matches the asset published in the GitHub
release::

    gh release verify-asset <version> pythonhere-*.apk -R b3b/pythonhere

This confirms that the local APK file matches the release asset recorded by
GitHub.

Verify the immutable GitHub release
-----------------------------------

Verify that GitHub recognizes the release as immutable::

    gh release verify <version> -R b3b/pythonhere

This confirms that the published release is protected by GitHub immutable
releases, so its release assets and associated Git tag cannot be changed after
publication.

Verify the Android signing certificate
--------------------------------------

Use Android SDK build-tools ``apksigner`` to verify the APK signature and print
the signing certificate::

    apksigner verify --verbose --print-certs pythonhere-*.apk

The printed certificate SHA-256 digest should match the expected PythonHere
Android signing certificate::

    3b725f0ca2485c56fac72248f4d42bfb5531e076d03b45c766fafca16de6a451
