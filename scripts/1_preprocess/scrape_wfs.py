"""Pull data from WFS

To explore data in QGIS, 'Add WFS layer' then connect to new server with url

To get metadata through ogrinfo::

    # list layers
    ogrinfo -ro 'WFS:https://ide.transporte.gob.ar/geoserver/ows?service=wfs&version=2.0.0&request=GetCapabilities'

    # layer metadata (where 'observ:_3.4.1.1.4.poste_km_25_view' is a layer name)
    ogrinfo -ro -so 'WFS:https://ide.transporte.gob.ar/geoserver/ows?service=wfs&version=2.0.0&request=GetCapabilities' observ:_3.4.1.1.4.poste_km_25_view

"""
import os
import sys
import requests
from bs4 import BeautifulSoup

def main(output_dir, server):
    """Download all layers from server to output_dir
    """
    url = '{}?service=wfs&version=2.0.0&request=GetCapabilities'.format(server)
    fname = os.path.join(output_dir, 'capabilities.xml')
    print(fname)
    if os.path.exists(fname):
        print(" * Reading")
        with open(fname, 'r') as fh:
            capabilities = fh.read()
    else:
        print(" * Downloading")
        r = requests.get(url)
        assert r.status_code == 200, "Failed to download capabilities"
        capabilities = r.text
        with open(fname, 'w') as fh:
            fh.write(capabilities)

    url_template = '{}?service=wfs&version=2.0.0&request=GetFeature&typeName={}'
    fname_template = '{}.gml'
    doc = BeautifulSoup(capabilities, 'xml')
    featuretypes = doc.find_all('FeatureType')
    for i, featuretype in enumerate(featuretypes):
        name = featuretype.find('Name').text
        print(" * Saving", i, "of", len(featuretypes), name)
        continue
        url = url_template.format(server, name)
        fname = os.path.join(output_dir, fname_template.format(name.replace(":", "-")))
        if not os.path.exists(fname):
            r = requests.get(url, stream=True)
            with open(fname, 'wb') as fd:
                for chunk in r.iter_content(chunk_size=1024):
                    fd.write(chunk)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        msg = "Usage: python {} https://server.url ./path/to/output_dir".format(sys.argv[0])
        msg += "\n"
        msg += " e.g.:\n       python {} https://ide.transporte.gob.ar/geoserver/ows ./data".format(sys.argv[0])
        exit(msg)
    SERVER = sys.argv[1]
    OUTPUT_DIR = sys.argv[2]
    main(OUTPUT_DIR, SERVER)
