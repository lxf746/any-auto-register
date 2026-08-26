#!/usr/bin/python3.12
# -*- coding: utf-8 -*-
#
# @Time  : 2026/7/6 19:25
# @File  : mailnest.py

from core.base_mailbox import MailNestMailBox  # noqa: F401
from providers.registry import register_provider

register_provider("mailbox", "mailnest_api")(MailNestMailBox)
