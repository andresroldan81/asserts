# -*- coding: utf-8 -*-

"""Software Composition Analysis for NuGet (C#) packages."""

# standard imports
import os

# 3rd party imports
from defusedxml.ElementTree import parse

# local imports
from fluidasserts.helper import sca
from fluidasserts import show_close
from fluidasserts import show_open
from fluidasserts import show_unknown
from fluidasserts.utils.decorators import track, level

PACKAGE_MANAGER = 'nuget'


def _get_requirements(path: str) -> list:
    """
    Get list of requirements from NuGet project.

    Files supported are packages.config

    :param path: Project path
    """
    reqs = []
    for root, _, files in os.walk(path):
        for pom_file in files:
            if pom_file != 'packages.config':
                continue
            full_path = os.path.join(root, pom_file)
            tree = parse(full_path)
            deps = tree.findall(".//package")
            for dep in deps:
                artifact_id = dep.attrib['id']
                version = dep.attrib['version']
                reqs.append((artifact_id, version))
    return reqs


@level('high')
@track
def package_has_vulnerabilities(package: str, version: str = None) -> bool:
    """
    Search vulnerabilities on given package/version.

    :param package: Package name.
    :param version: Package version.
    """
    try:
        vulns = sca.get_vulns_ossindex(PACKAGE_MANAGER, package, version)
        if vulns:
            show_open('Software has vulnerabilities',
                      details=dict(package=package, version=version,
                                   vuln_num=len(vulns), vulns=vulns))
            return True
        show_close('Software doesn\'t have vulnerabilities',
                   details=dict(package=package, version=version))
        return False
    except sca.ConnError as exc:
        show_unknown('Could not connect to SCA provider',
                     details=dict(error=str(exc).replace(':', ',')))
        return False
    except sca.PackageNotFoundException:
        show_unknown('Sofware couldn\'t be found in package manager',
                     details=dict(package=package, version=version))
        return False


@track
def project_has_vulnerabilities(path: str) -> bool:
    """
    Search vulnerabilities on given project directory.

    :param path: Project path.
    """
    try:
        reqs = _get_requirements(path)
        response = sca.scan_requirements(reqs, PACKAGE_MANAGER)
    except sca.ConnError as exc:
        show_unknown('Could not connect to SCA provider',
                     details=dict(error=str(exc).replace(':', ',')))
        return False

    if not response:
        show_unknown('Not packages found in project',
                     details=dict(path=path))
        return False

    result = False
    for package in response:
        if package['version'] == -1:
            continue
        ret = package_has_vulnerabilities(package['package'],
                                          package['version'])
        if ret:
            result = True
    return result
