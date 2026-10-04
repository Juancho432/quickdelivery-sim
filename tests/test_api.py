import os
import sys
from pathlib import Path

# Agregar raíz del proyecto al sys.path para permitir ejecución directa
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import unittest

# Importar todas las suites temáticas modulares
from tests.test_devops_telemetry import TestDevOpsAndTelemetry
from tests.test_config import TestSystemConfiguration
from tests.test_orders import TestClientOrderFlow
from tests.test_kds import TestKitchenKDSFlow
from tests.test_couriers import TestCourierLifecycleAndDispatch
from tests.test_business_logic import TestBusinessLogicAndEdgeCases
from tests.test_end_to_end import TestEndToEndCompleteFlows
from tests.test_live_api import TestLiveApiConnectivity

__all__ = [
    "TestDevOpsAndTelemetry",
    "TestSystemConfiguration",
    "TestClientOrderFlow",
    "TestKitchenKDSFlow",
    "TestCourierLifecycleAndDispatch",
    "TestBusinessLogicAndEdgeCases",
    "TestEndToEndCompleteFlows",
    "TestLiveApiConnectivity",
]

if __name__ == "__main__":
    unittest.main()
