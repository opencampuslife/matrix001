package revocationservice

import (
	"encoding/json"
	"net/http"

	"github.com/gaokao-agent/matrix-mother/internal/agent-registry"
	"github.com/gaokao-agent/matrix-mother/internal/types"
)

type Service struct {
	store       agentregistry.Store
	revocations []*types.RevocationEntry
}

func NewService(store agentregistry.Store) *Service {
	return &Service{
		store:       store,
		revocations: make([]*types.RevocationEntry, 0),
	}
}

type RevokeRequest struct {
	RevocationType string `json:"revocation_type"`
	TargetID       string `json:"target_id"`
	Reason         string `json:"reason"`
}

func (s *Service) RegisterRoutes(mux *http.ServeMux) {
	mux.HandleFunc("POST /revocations", s.handleRevoke)
	mux.HandleFunc("GET /revocations", s.handleListRevocations)
	mux.HandleFunc("GET /revocations/{revocation_id}", s.handleGetRevocation)
}

func (s *Service) handleRevoke(w http.ResponseWriter, r *http.Request) {
	var req RevokeRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid request body"})
		return
	}

	validTypes := map[string]bool{"agent": true, "capability": true, "knowledge_version": true, "policy": true}
	if !validTypes[req.RevocationType] {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid revocation_type"})
		return
	}

	if req.RevocationType == "agent" {
		if err := s.store.UpdateAgentStatus(req.TargetID, false); err != nil {
			writeJSON(w, http.StatusNotFound, map[string]string{"error": "agent not found"})
			return
		}
	}

	entry := &types.RevocationEntry{
		RevocationID:   types.NewRevocationID(),
		RevocationType: req.RevocationType,
		TargetID:       req.TargetID,
		Reason:         req.Reason,
		EffectiveFrom:  types.NowISO(),
		IssuedAt:       types.NowISO(),
		Signature:      "", // TODO: sign with ML-DSA-65
	}
	s.revocations = append(s.revocations, entry)

	writeJSON(w, http.StatusCreated, entry)
}

func (s *Service) handleListRevocations(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, s.revocations)
}

func (s *Service) handleGetRevocation(w http.ResponseWriter, r *http.Request) {
	revID := r.PathValue("revocation_id")
	for _, rev := range s.revocations {
		if rev.RevocationID == revID {
			writeJSON(w, http.StatusOK, rev)
			return
		}
	}
	writeJSON(w, http.StatusNotFound, map[string]string{"error": "revocation not found"})
}

func writeJSON(w http.ResponseWriter, status int, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}
