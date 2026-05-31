package agentregistry

import (
	"encoding/json"
	"fmt"
	"net/http"
	"sync"

	"github.com/gaokao-agent/matrix-mother/internal/types"
)

type Store interface {
	SaveAgent(agent *types.Agent) error
	GetAgent(agentID string) (*types.Agent, error)
	ListAgents() ([]*types.Agent, error)
	UpdateAgentStatus(agentID string, active bool) error
	DeleteAgent(agentID string) error
}

type MemoryStore struct {
	mu     sync.RWMutex
	agents map[string]*types.Agent
}

func NewMemoryStore() *MemoryStore {
	return &MemoryStore{agents: make(map[string]*types.Agent)}
}

func (s *MemoryStore) SaveAgent(agent *types.Agent) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.agents[agent.AgentID] = agent
	return nil
}

func (s *MemoryStore) GetAgent(agentID string) (*types.Agent, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	a, ok := s.agents[agentID]
	if !ok {
		return nil, fmt.Errorf("agent %s not found", agentID)
	}
	return a, nil
}

func (s *MemoryStore) ListAgents() ([]*types.Agent, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	result := make([]*types.Agent, 0, len(s.agents))
	for _, a := range s.agents {
		result = append(result, a)
	}
	return result, nil
}

func (s *MemoryStore) UpdateAgentStatus(agentID string, active bool) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	a, ok := s.agents[agentID]
	if !ok {
		return fmt.Errorf("agent %s not found", agentID)
	}
	a.Active = active
	return nil
}

func (s *MemoryStore) DeleteAgent(agentID string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	delete(s.agents, agentID)
	return nil
}

type Service struct {
	store Store
}

func NewService(store Store) *Service {
	return &Service{store: store}
}

type RegisterRequest struct {
	AgentType     string   `json:"agent_type"`
	ParentID      string   `json:"parent_id"`
	KEMPubKey     string   `json:"kem_public_key"`
	SigningKey    string   `json:"signing_public_key"`
	Roles         []string `json:"requested_roles"`
	DeviceAttest  string   `json:"device_attestation,omitempty"`
}

func (s *Service) RegisterRoutes(mux *http.ServeMux) {
	mux.HandleFunc("POST /agents/register", s.handleRegister)
	mux.HandleFunc("GET /agents/{agent_id}", s.handleGetAgent)
	mux.HandleFunc("GET /agents", s.handleListAgents)
	mux.HandleFunc("DELETE /agents/{agent_id}", s.handleDeregister)
}

func (s *Service) handleRegister(w http.ResponseWriter, r *http.Request) {
	var req RegisterRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid request body"})
		return
	}

	if req.AgentType != "mother" && req.AgentType != "child" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "agent_type must be mother or child"})
		return
	}
	if len(req.Roles) == 0 {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "at least one role is required"})
		return
	}

	agent := &types.Agent{
		AgentID:    types.GenerateID(req.AgentType),
		AgentType:  req.AgentType,
		ParentID:   req.ParentID,
		KEMPubKey:  req.KEMPubKey,
		SigningKey: req.SigningKey,
		Roles:      req.Roles,
		CreatedAt:  types.NowISO(),
		Active:     true,
	}

	if err := s.store.SaveAgent(agent); err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": err.Error()})
		return
	}

	writeJSON(w, http.StatusCreated, agent)
}

func (s *Service) handleGetAgent(w http.ResponseWriter, r *http.Request) {
	agentID := r.PathValue("agent_id")
	agent, err := s.store.GetAgent(agentID)
	if err != nil {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "agent not found"})
		return
	}
	writeJSON(w, http.StatusOK, agent)
}

func (s *Service) handleListAgents(w http.ResponseWriter, r *http.Request) {
	agents, err := s.store.ListAgents()
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": err.Error()})
		return
	}
	writeJSON(w, http.StatusOK, agents)
}

func (s *Service) handleDeregister(w http.ResponseWriter, r *http.Request) {
	agentID := r.PathValue("agent_id")
	if err := s.store.UpdateAgentStatus(agentID, false); err != nil {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "agent not found"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "deactivated", "agent_id": agentID})
}

func writeJSON(w http.ResponseWriter, status int, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}
