package types

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"time"
)

type AgentKind string

const (
	MotherAgent AgentKind = "mother"
	ChildAgent  AgentKind = "child"
)

type Agent struct {
	AgentID     string   `json:"agent_id"`
	AgentType   string   `json:"agent_type"`
	ParentID    string   `json:"parent_id"`
	KEMPubKey   string   `json:"kem_public_key"`
	SigningKey  string   `json:"signing_public_key"`
	Roles       []string `json:"requested_roles"`
	CreatedAt   string   `json:"created_at"`
	Active      bool     `json:"active"`
}

type CapabilityToken struct {
	CapabilityID     string   `json:"capability_id"`
	AgentID          string   `json:"agent_id"`
	Roles            []string `json:"roles"`
	AllowedKnowledge []string `json:"allowed_knowledge"`
	AllowedTools     []string `json:"allowed_tools"`
	DeniedTools      []string `json:"denied_tools"`
	OfflineAllowed   bool     `json:"offline_allowed"`
	OfflineExpiry    string   `json:"offline_expiry"`
	MaxOfflineActions int    `json:"max_offline_actions"`
	PolicyHash       string   `json:"policy_hash"`
	IssuedAt         string   `json:"issued_at"`
	Signature        string   `json:"issuer_signature"`
	Revoked          bool     `json:"revoked"`
}

type RevocationEntry struct {
	RevocationID   string `json:"revocation_id"`
	RevocationType string `json:"revocation_type"`
	TargetID       string `json:"target_id"`
	Reason         string `json:"reason"`
	EffectiveFrom  string `json:"effective_from"`
	IssuedAt       string `json:"issued_at"`
	Signature      string `json:"signature"`
}

type KnowledgeManifest struct {
	KnowledgeVersion string            `json:"knowledge_version"`
	PreviousVersion  string            `json:"previous_version"`
	ManifestHash     string            `json:"manifest_hash"`
	MerkleRoot       string            `json:"merkle_root"`
	PolicyHash       string            `json:"policy_hash"`
	Packages         []KnowledgePackage `json:"packages"`
	Issuer           string            `json:"issuer"`
	IssuedAt         string            `json:"issued_at"`
	Signature        string            `json:"signature"`
}

type KnowledgePackage struct {
	PackageID    string   `json:"package_id"`
	CID          string   `json:"cid"`
	Hash         string   `json:"hash"`
	RoleTags     []string `json:"role_tags"`
	EncryptedDEK string   `json:"encrypted_dek"`
}

func GenerateID(prefix string) string {
	b := make([]byte, 8)
	rand.Read(b)
	return fmt.Sprintf("did:matrix:%s:%s", prefix, hex.EncodeToString(b))
}

func NewCapabilityTokenID() string {
	b := make([]byte, 6)
	rand.Read(b)
	return fmt.Sprintf("cap_%s", hex.EncodeToString(b))
}

func NewRevocationID() string {
	b := make([]byte, 6)
	rand.Read(b)
	return fmt.Sprintf("rev_%s", hex.EncodeToString(b))
}

func NowISO() string {
	return time.Now().UTC().Format(time.RFC3339)
}
