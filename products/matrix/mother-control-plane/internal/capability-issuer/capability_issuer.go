package capabilityissuer

import (
	"encoding/json"
	"net/http"
	"time"

	"github.com/gaokao-agent/matrix-mother/internal/agent-registry"
	"github.com/gaokao-agent/matrix-mother/internal/types"
)

type Service struct {
	store agentregistry.Store
}

func NewService(store agentregistry.Store) *Service {
	return &Service{store: store}
}

type IssueRequest struct {
	AgentID           string   `json:"agent_id"`
	Roles             []string `json:"roles"`
	AllowedKnowledge  []string `json:"allowed_knowledge"`
	AllowedTools      []string `json:"allowed_tools"`
	DeniedTools       []string `json:"denied_tools"`
	OfflineAllowed    bool     `json:"offline_allowed"`
	OfflineTTLHours   int      `json:"offline_ttl_hours"`
	MaxOfflineActions int      `json:"max_offline_actions"`
	PolicyHash        string   `json:"policy_hash"`
}

func (s *Service) RegisterRoutes(mux *http.ServeMux) {
	mux.HandleFunc("POST /capabilities/issue", s.handleIssue)
	mux.HandleFunc("GET /capabilities/{capability_id}", s.handleGet)
	mux.HandleFunc("POST /capabilities/{capability_id}/revoke", s.handleRevoke)
}

func (s *Service) handleIssue(w http.ResponseWriter, r *http.Request) {
	var req IssueRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid request body"})
		return
	}

	agent, err := s.store.GetAgent(req.AgentID)
	if err != nil {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "agent not found"})
		return
	}
	if !agent.Active {
		writeJSON(w, http.StatusForbidden, map[string]string{"error": "agent is not active"})
		return
	}

	if req.MaxOfflineActions <= 0 {
		req.MaxOfflineActions = 500
	}
	if req.OfflineTTLHours <= 0 {
		req.OfflineTTLHours = 168
	}

	capability := &types.CapabilityToken{
		CapabilityID:      types.NewCapabilityTokenID(),
		AgentID:           req.AgentID,
		Roles:             req.Roles,
		AllowedKnowledge:  req.AllowedKnowledge,
		AllowedTools:      req.AllowedTools,
		DeniedTools:       req.DeniedTools,
		OfflineAllowed:    req.OfflineAllowed,
		OfflineExpiry:     time.Now().UTC().Add(time.Duration(req.OfflineTTLHours) * time.Hour).Format(time.RFC3339),
		MaxOfflineActions: req.MaxOfflineActions,
		PolicyHash:        req.PolicyHash,
		IssuedAt:          types.NowISO(),
		Signature:         "", // TODO: sign with ML-DSA-65 signing key
	}

	writeJSON(w, http.StatusCreated, capability)
}

func (s *Service) handleGet(w http.ResponseWriter, r *http.Request) {
	// TODO: persist capabilities in store
	writeJSON(w, http.StatusNotFound, map[string]string{"error": "capability persistence not yet implemented"})
}

func (s *Service) handleRevoke(w http.ResponseWriter, r *http.Request) {
	capabilityID := r.PathValue("capability_id")
	writeJSON(w, http.StatusOK, map[string]string{
		"status":        "revoked",
		"capability_id": capabilityID,
	})
}

func writeJSON(w http.ResponseWriter, status int, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}
