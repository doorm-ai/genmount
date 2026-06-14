# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 DOORM AI PTE. LTD. and Genmount OS Contributors

from __future__ import annotations


class GenmountError(Exception):

    exit_code: int = 1


class ConfigError(GenmountError):

    exit_code = 2


class NotActivatedError(GenmountError):

    exit_code = 3


class OllamaUnavailableError(GenmountError):

    exit_code = 4


class CloudUnavailableError(GenmountError):

    exit_code = 5


class IntegrityError(GenmountError):

    exit_code = 6
