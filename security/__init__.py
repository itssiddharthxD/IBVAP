"""Security / Suspicious Activity layer.

Architecture:
  Rule Manager → Analytics Engine → Alert / Event Manager

AI tasks answer: "What can the camera detect?"
Security rules answer: "What should happen when something is detected?"
"""
from security.rule_manager import RuleManager
from security.analytics_engine import AnalyticsEngine
from security.alert_manager import AlertManager
from security.rule_types import RULE_TYPES, list_rule_types, rule_type_label

__all__ = [
    "RuleManager",
    "AnalyticsEngine",
    "AlertManager",
    "RULE_TYPES",
    "list_rule_types",
    "rule_type_label",
]
