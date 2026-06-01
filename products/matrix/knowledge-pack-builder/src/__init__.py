"""
Knowledge Pack Builder — transforms source knowledge into encrypted, signed,
and manifest-tracked knowledge packs for distribution to child agents.

Pipeline:
    1. Chunk source documents
    2. Encrypt each chunk package with AES-256-GCM
    3. Wrap DEK with ML-KEM-768 for each authorized role
    4. Build Merkle tree over all packages
    5. Sign manifest with ML-DSA-65
    6. Publish manifest + anchor root on-chain
"""

__version__ = "0.1.0"
