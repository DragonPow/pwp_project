#!/usr/bin/env python
# Copyright (c) 2025, Government Agency and contributors
# For license information, please see license.txt

import sys
import os
import unittest

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_all_tests():
    """Run all tests for the PWP Project application"""

    # Import test modules
    from pwp_project.pwp_project.doctype.digital_signature.test_digital_signature import TestDigitalSignature
    from pwp_project.pwp_project.doctype.user_crypto_keys.test_user_crypto_keys import TestUserCryptoKeys
    from pwp_project.pwp_project.doctype.workflow_definition.test_workflow_definition import TestWorkflowDefinition
    from pwp_project.pwp_project.doctype.workflow_instance.test_workflow_instance import TestWorkflowInstance
    from pwp_project.pwp_project.doctype.document_version.test_document_version import TestDocumentVersion

    # Create test suite
    test_suite = unittest.TestSuite()

    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestDigitalSignature))
    test_suite.addTest(unittest.makeSuite(TestUserCryptoKeys))
    test_suite.addTest(unittest.makeSuite(TestWorkflowDefinition))
    test_suite.addTest(unittest.makeSuite(TestWorkflowInstance))
    test_suite.addTest(unittest.makeSuite(TestDocumentVersion))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Return success status
    return result.wasSuccessful()

def run_specific_test(test_name):
    """Run a specific test module"""

    if test_name == "digital_signature":
        from pwp_project.pwp_project.doctype.digital_signature.test_digital_signature import TestDigitalSignature
        test_suite = unittest.makeSuite(TestDigitalSignature)
    elif test_name == "user_crypto_keys":
        from pwp_project.pwp_project.doctype.user_crypto_keys.test_user_crypto_keys import TestUserCryptoKeys
        test_suite = unittest.makeSuite(TestUserCryptoKeys)
    elif test_name == "workflow_definition":
        from pwp_project.pwp_project.doctype.workflow_definition.test_workflow_definition import TestWorkflowDefinition
        test_suite = unittest.makeSuite(TestWorkflowDefinition)
    elif test_name == "workflow_instance":
        from pwp_project.pwp_project.doctype.workflow_instance.test_workflow_instance import TestWorkflowInstance
        test_suite = unittest.makeSuite(TestWorkflowInstance)
    elif test_name == "document_version":
        from pwp_project.pwp_project.doctype.document_version.test_document_version import TestDocumentVersion
        test_suite = unittest.makeSuite(TestDocumentVersion)
    else:
        print(f"Unknown test module: {test_name}")
        print("Available test modules:")
        print("  - digital_signature")
        print("  - user_crypto_keys")
        print("  - workflow_definition")
        print("  - workflow_instance")
        print("  - document_version")
        return False

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Return success status
    return result.wasSuccessful()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        success = run_specific_test(test_name)
    else:
        # Run all tests
        success = run_all_tests()

    # Exit with appropriate code
    sys.exit(0 if success else 1)
