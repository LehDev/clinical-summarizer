"""
Funções de hash para anonimização de identificadores.

O ETL armazena patient_id e visit_id como hashes SHA-256.
Este módulo fornece a mesma função de hash para que a API
possa converter IDs originais recebidos do frontend.
"""

import hashlib


def hash_id(original_id: str) -> str:
    """
    Converte um ID original para hash SHA-256.

    Args:
        original_id: ID original (ex: número do paciente do sistema fonte).

    Returns:
        Hash SHA-256 hexadecimal (64 caracteres).

    Example:
        >>> hash_id("12345")
        '5994471abb01112afcc18159f6cc74b4f511b99806da59b3caf5a9c173cacfc5'
    """
    return hashlib.sha256(original_id.encode("utf-8")).hexdigest()
