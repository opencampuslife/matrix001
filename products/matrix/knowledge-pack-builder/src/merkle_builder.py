"""
Merkle Builder — constructs a Merkle tree over all knowledge packages
in a release and produces a single Merkle root for on-chain anchoring.
"""

import hashlib
from dataclasses import dataclass
from typing import Optional


@dataclass
class MerkleNode:
    hash: str
    left: Optional["MerkleNode"] = None
    right: Optional["MerkleNode"] = None


class MerkleBuilder:
    def __init__(self, hash_algorithm: str = "sha384"):
        self.hash_algorithm = hash_algorithm
        self._hasher = hashlib.new(hash_algorithm)

    def hash_data(self, data: bytes) -> str:
        h = self._hasher.copy()
        h.update(data)
        return h.hexdigest()

    def hash_pair(self, left: str, right: str) -> str:
        h = self._hasher.copy()
        h.update(bytes.fromhex(left))
        h.update(bytes.fromhex(right))
        return h.hexdigest()

    def build_from_packages(self, packages: list[dict]) -> tuple[str, list[str]]:
        if not packages:
            return "0x" + "0" * 96, []

        hashes = []
        for pkg in packages:
            data = f"{pkg['package_id']}:{pkg['hash']}".encode()
            hashes.append(self.hash_data(data))

        # Build layers
        layer = hashes[:]
        proof_layers = [layer[:]]
        while len(layer) > 1:
            next_layer = []
            for i in range(0, len(layer), 2):
                if i + 1 < len(layer):
                    next_layer.append(self.hash_pair(layer[i], layer[i + 1]))
                else:
                    next_layer.append(layer[i])
            proof_layers.append(next_layer[:])
            layer = next_layer

        merkle_root = "0x" + layer[0] if layer else "0x" + "0" * 96
        return merkle_root, hashes

    def generate_proof(self, leaf_hash: str, leaf_hashes: list[str]) -> list[dict]:
        proof = []
        idx = leaf_hashes.index(leaf_hash)
        layer = leaf_hashes[:]
        while len(layer) > 1:
            sibling_idx = idx ^ 1
            if sibling_idx < len(layer):
                position = "left" if sibling_idx < idx else "right"
                proof.append({
                    "sibling_hash": layer[sibling_idx],
                    "position": position,
                })
            # Move up
            layer = self._next_layer(layer)
            idx = idx // 2
        return proof

    def verify_proof(self, leaf_hash: str, merkle_root: str, proof: list[dict]) -> bool:
        computed = leaf_hash
        for step in proof:
            if step["position"] == "left":
                computed = self.hash_pair(step["sibling_hash"], computed)
            else:
                computed = self.hash_pair(computed, step["sibling_hash"])
        return "0x" + computed == merkle_root

    def _next_layer(self, layer: list[str]) -> list[str]:
        next_layer = []
        for i in range(0, len(layer), 2):
            if i + 1 < len(layer):
                next_layer.append(self.hash_pair(layer[i], layer[i + 1]))
            else:
                next_layer.append(layer[i])
        return next_layer
