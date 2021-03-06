import sys
import re
from collections import defaultdict

# preload XML
import xml.etree.cElementTree as ET
import defusedxml.cElementTree as DET
import re
import glob

xmlstring = []



def parse_dbs(folder):
    """
    parse the XML dbs and build an in-memory lookup
    :param folder: the folder full of *.xml files
    :return:
    """
    root = None
    for filename in glob.glob(folder+'/*.xml'):
        with open(filename) as f:
            db_string = f.read() # remove the annoying namespace
            db_string = re.sub(' xmlns="[^"]+"', '', db_string, count=1)
            # xmlstring.append(db_string)
            data = ET.fromstring(db_string)
            if root is None:
                root = data
            else:
                root.extend(data)

    return root


#root = ET.fromstring("\n".join(xmlstring))
# namespace ="http://nvd.nist.gov/feeds/cve/1.2"

def etree_to_dict(t):
    """
    Change the xml tree to an easy to use python dict
    :param t: the xml tree
    :return: a dict representation
    """
    d = {t.tag: {} if t.attrib else None}
    children = list(t)
    if children:
        dd = defaultdict(list)
        for dc in map(etree_to_dict, children):
            for k, v in dc.iteritems():
                dd[k].append(v)
        d = {t.tag: {k:v[0] if len(v) == 1 else v for k, v in dd.iteritems()}}
    if t.attrib:
        d[t.tag].update(('@' + k, v) for k, v in t.attrib.iteritems())
    if t.text:
        text = t.text.strip()
        if children or t.attrib:
            if text:
              d[t.tag]['#text'] = text
        else:
            d[t.tag] = text
    return d


def get_packages_swid(package_list):
    """
    Get the packages from a swid string
    :param package_strs:
    :return:
    """
    package_xml = None
    packages = defaultdict(set)
    errors = []
    for xml_doc in package_list.split("\n"):
        try:
            # remove the <? ?> if any
            xml_doc = re.sub('<\?[^>]+\?>', '', xml_doc)
            # use DET since this is untrusted data
            data = DET.fromstring(xml_doc)
            name, version = data.attrib['name'], data.attrib['version']
            version = version.split("-")[0]
            packages[name].add(version)

        except Exception as e:
            errors.append(str(e))

    return errors, packages

def get_packages_rpm(package_list):
    """
    Get the packages from an rpm string
    :param package_strs:
    :return:
    """
    package_strs = package_list.split("\n")
    packages = defaultdict(set)
    errors = []
    for x in package_strs:
        m = re.search(r'(.*/)*(.*)-(.*)-(.*?)\.(.*)', x)
        if m:
            (path, name, version, release, platform) = m.groups()
            path = path or ''
            verrel = version + '-' + release
            packages[name].add(version)
            # print "\t".join([path, name, verrel, version, release, platform])
        else:
            errors.append('ERROR: Invalid name: %s\n' % x)

    return errors, packages

def get_package_dict(package_list):
    """
    Get the packages from the string
    :param package_strs:
    :return:
    """
    if package_list.startswith("<?xml"):
        return get_packages_swid(package_list)
    else:
        return get_packages_rpm(package_list)


def get_vulns(packages, root):
    """
    Get the vulns from a list of packages returned by get_package_dict()
    :param packages:
    :return:
    """
    result = defaultdict(list)
    for entry in root:
        for vuln_soft in entry.findall("vuln_soft"):
            for prod in vuln_soft.findall("prod"):
                if prod.attrib['name'] in packages:
                    vers = set([x.attrib['num'] for x in prod.findall("vers")])
                    intersection = set(vers).intersection(packages[prod.attrib['name']])
                    if len(intersection) > 0:
                        si = ' - ' + ','.join(intersection)
                        result[prod.attrib['name'] + si].append(etree_to_dict(entry)["entry"])
    return result
