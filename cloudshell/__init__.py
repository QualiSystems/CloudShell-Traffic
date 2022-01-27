"""
This __init__ is here just to allow proper testing, it is not added to Cloudshell-Traffic package.

Cloudshell-Traffic is subpackage of Cloudshell. Wherever it will be installed, it will be under Cloudshell and alongside other
Cloudshell subpackages. The __init__ file of the parent Cloudshell package should come from official Cloudshell installations,
not from Cloudshell-Traffic.
"""
from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)
