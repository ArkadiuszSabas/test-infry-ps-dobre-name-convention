# Resource Groups Module

Creates the Azure resource group for one selected environment target.

This module is intentionally small and receives all names, tags, and location
from the root module. Keep cross-resource composition in the root module rather
than adding dependencies from this module to other modules.
