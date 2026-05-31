package agentregistry_test

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gaokao-agent/matrix-mother/internal/agentregistry"
)

func TestRegisterAgent(t *testing.T) {
	store := agentregistry.NewMemoryStore()
	svc := agentregistry.NewService(store)

	body := map[string]interface{}{
		"agent_type":      "child",
		"parent_id":       "did:matrix:mother:root",
		"kem_public_key":   "base64-ml-kem-pubkey",
		"signing_public_key": "base64-ml-dsa-pubkey",
		"requested_roles":  []string{"campus_edge_assistant"},
	}
	b, _ := json.Marshal(body)

	req := httptest.NewRequest("POST", "/agents/register", bytes.NewReader(b))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	svc.RegisterRoutes(http.NewServeMux())
	svc.RegisterRoutes(nil)

	// Workaround: test handler directly via a new mux
	mux := http.NewServeMux()
	svc.RegisterRoutes(mux)
	mux.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("expected 201, got %d: %s", w.Code, w.Body.String())
	}

	var agent map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &agent)
	if agent["agent_type"] != "child" {
		t.Errorf("expected child agent, got %v", agent["agent_type"])
	}
	if agent["agent_id"] == "" {
		t.Error("expected agent_id to be set")
	}
}

func TestGetAgentNotFound(t *testing.T) {
	store := agentregistry.NewMemoryStore()
	svc := agentregistry.NewService(store)

	mux := http.NewServeMux()
	svc.RegisterRoutes(mux)

	req := httptest.NewRequest("GET", "/agents/nonexistent", nil)
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected 404, got %d", w.Code)
	}
}

func TestListAgentsEmpty(t *testing.T) {
	store := agentregistry.NewMemoryStore()
	svc := agentregistry.NewService(store)

	mux := http.NewServeMux()
	svc.RegisterRoutes(mux)

	req := httptest.NewRequest("GET", "/agents", nil)
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", w.Code)
	}
}

func TestDeregisterAgent(t *testing.T) {
	store := agentregistry.NewMemoryStore()
	svc := agentregistry.NewService(store)

	body := map[string]interface{}{
		"agent_type":      "child",
		"parent_id":       "did:matrix:mother:root",
		"kem_public_key":   "base64-ml-kem-pubkey",
		"signing_public_key": "base64-ml-dsa-pubkey",
		"requested_roles":  []string{"campus_edge_assistant"},
	}
	b, _ := json.Marshal(body)

	mux := http.NewServeMux()
	svc.RegisterRoutes(mux)

	req := httptest.NewRequest("POST", "/agents/register", bytes.NewReader(b))
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	var agent map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &agent)
	agentID := agent["agent_id"].(string)

	req2 := httptest.NewRequest("DELETE", "/agents/"+agentID, nil)
	w2 := httptest.NewRecorder()
	mux.ServeHTTP(w2, req2)

	if w2.Code != http.StatusOK {
		t.Errorf("expected 200, got %d: %s", w2.Code, w2.Body.String())
	}
}

func TestRegisterInvalidAgentType(t *testing.T) {
	store := agentregistry.NewMemoryStore()
	svc := agentregistry.NewService(store)

	body := map[string]interface{}{
		"agent_type":      "invalid_type",
		"parent_id":       "did:matrix:mother:root",
		"kem_public_key":   "key",
		"signing_public_key": "key",
		"requested_roles":  []string{},
	}
	b, _ := json.Marshal(body)

	mux := http.NewServeMux()
	svc.RegisterRoutes(mux)
	req := httptest.NewRequest("POST", "/agents/register", bytes.NewReader(b))
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", w.Code)
	}
}
