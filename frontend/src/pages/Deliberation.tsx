/**
 * Council of Minds Deliberation Page
 * Main interface for submitting queries and viewing deliberation results
 */

import React, { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { DeliberationForm } from '@/components/council/DeliberationForm';
import { DeliberationResults } from '@/components/council/DeliberationResults';
import { PersonaCards } from '@/components/council/PersonaCards';
import { DeliberationHistory } from '@/components/council/DeliberationHistory';
import { DeliberationProgress } from '@/components/council/DeliberationProgress';
import type {
  DeliberationResponse,
  PersonaInfo,
  DeliberationHistory as HistoryType,
  CouncilHealthCheck,
} from '@/types';

export function Deliberation() {
  const [currentDeliberation, setCurrentDeliberation] = useState<DeliberationResponse | null>(null);
  const [personas, setPersonas] = useState<PersonaInfo[]>([]);
  const [history, setHistory] = useState<HistoryType | null>(null);
  const [health, setHealth] = useState<CouncilHealthCheck | null>(null);
  const [loading, setLoading] = useState({
    deliberation: false,
    personas: false,
    history: false,
    health: false,
  });
  const [error, setError] = useState<string | null>(null);
  const [activeDeliberationId, setActiveDeliberationId] = useState<string | null>(null);

  // Load initial data
  useEffect(() => {
    loadPersonas();
    loadHistory();
    loadHealth();
  }, []);

  const loadPersonas = async () => {
    setLoading(prev => ({ ...prev, personas: true }));
    try {
      const data = await apiClient.getPersonas();
      setPersonas(data);
    } catch (err) {
      console.error('Failed to load personas:', err);
      setError('Failed to load personas');
    } finally {
      setLoading(prev => ({ ...prev, personas: false }));
    }
  };

  const loadHistory = async () => {
    setLoading(prev => ({ ...prev, history: true }));
    try {
      const data = await apiClient.getDeliberationHistory(10);
      setHistory(data);
    } catch (err) {
      console.error('Failed to load history:', err);
      // Don't show error for history - it's not critical
    } finally {
      setLoading(prev => ({ ...prev, history: false }));
    }
  };

  const loadHealth = async () => {
    setLoading(prev => ({ ...prev, health: true }));
    try {
      const data = await apiClient.getCouncilHealth();
      setHealth(data);
    } catch (err) {
      console.error('Failed to load health:', err);
      // Don't show error for health - it's not critical
    } finally {
      setLoading(prev => ({ ...prev, health: false }));
    }
  };

  const handleDeliberationSubmit = async (query: string, context: Record<string, any>) => {
    setLoading(prev => ({ ...prev, deliberation: true }));
    setError(null);
    setCurrentDeliberation(null);

    // Generate a temporary deliberation ID for real-time tracking
    const tempDeliberationId = `delib_${Date.now()}`;
    setActiveDeliberationId(tempDeliberationId);

    try {
      const response = await apiClient.submitDeliberation({
        query,
        context,
        timeout: 60, // 1 minute timeout
      });
      
      setCurrentDeliberation(response);
      
      // Reload history after successful deliberation
      setTimeout(() => {
        loadHistory();
      }, 1000);
      
    } catch (err) {
      console.error('Deliberation failed:', err);
      setError(err instanceof Error ? err.message : 'Deliberation failed');
    } finally {
      setLoading(prev => ({ ...prev, deliberation: false }));
      setActiveDeliberationId(null);
    }
  };

  const handleDeliberationComplete = (result: any) => {
    setActiveDeliberationId(null);
    setLoading(prev => ({ ...prev, deliberation: false }));
    // The result should already be set by the API response
    loadHistory();
  };

  const handleDeliberationError = (errorMessage: string) => {
    setActiveDeliberationId(null);
    setLoading(prev => ({ ...prev, deliberation: false }));
    setError(errorMessage);
  };

  const handleReset = async () => {
    try {
      await apiClient.resetCouncil();
      setCurrentDeliberation(null);
      setHistory(null);
      loadHealth();
      loadHistory();
    } catch (err) {
      console.error('Failed to reset council:', err);
      setError('Failed to reset council');
    }
  };

  const isCouncilHealthy = health?.status === 'healthy' && health?.orchestrator?.initialized;

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Council of Minds</h1>
            <p className="text-gray-600 mt-2">
              Submit queries for deliberation by AI personas with different expertise and perspectives
            </p>
          </div>
          <div className="flex items-center gap-4">
            {health && (
              <div className="flex items-center gap-2">
                <StatusBadge status={isCouncilHealthy ? 'running' : 'stopped'} />
                <span className="text-sm text-gray-600">
                  {health.orchestrator?.personas_loaded || 0} personas loaded
                </span>
              </div>
            )}
            <button
              onClick={handleReset}
              className="px-4 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
              title="Reset Council State"
            >
              Reset
            </button>
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Error</h3>
              <div className="mt-2 text-sm text-red-700">
                <p>{error}</p>
              </div>
            </div>
          </div>
          <button
            onClick={() => setError(null)}
            className="ml-auto text-red-600 hover:text-red-800"
          >
            ×
          </button>
        </div>
      )}

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Form and Results */}
        <div className="lg:col-span-2 space-y-6">
          {/* Deliberation Form */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Submit Query</h2>
            {!isCouncilHealthy ? (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <p className="text-yellow-800">
                  Council is not ready. Please wait for personas to load or check system health.
                </p>
              </div>
            ) : (
              <DeliberationForm
                onSubmit={handleDeliberationSubmit}
                loading={loading.deliberation}
                personas={personas}
              />
            )}
          </div>

          {/* Real-time Progress */}
          {activeDeliberationId && (
            <div className="bg-white rounded-lg shadow p-6">
              <DeliberationProgress
                deliberationId={activeDeliberationId}
                onComplete={handleDeliberationComplete}
                onError={handleDeliberationError}
              />
            </div>
          )}

          {/* Current Deliberation Results */}
          {currentDeliberation && !activeDeliberationId && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-4">Current Deliberation</h2>
              <DeliberationResults deliberation={currentDeliberation} />
            </div>
          )}
        </div>

        {/* Right Column: Personas and History */}
        <div className="space-y-6">
          {/* Personas */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Available Personas</h2>
            {loading.personas ? (
              <LoadingSpinner size="sm" />
            ) : personas.length > 0 ? (
              <PersonaCards personas={personas} />
            ) : (
              <p className="text-gray-500">No personas available</p>
            )}
          </div>

          {/* Recent History */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Recent Deliberations</h2>
            {loading.history ? (
              <LoadingSpinner size="sm" />
            ) : history ? (
              <DeliberationHistory
                history={history}
                onSelectDeliberation={setCurrentDeliberation}
              />
            ) : (
              <p className="text-gray-500">No recent deliberations</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}