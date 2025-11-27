/**
 * Deliberation Form Component
 * Form for submitting queries to the Council of Minds
 */

import React, { useState } from 'react';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import type { PersonaInfo } from '@/types';

interface DeliberationFormProps {
  onSubmit: (query: string, context: Record<string, any>) => Promise<void>;
  loading: boolean;
  personas: PersonaInfo[];
}

export function DeliberationForm({ onSubmit, loading, personas }: DeliberationFormProps) {
  const [query, setQuery] = useState('');
  const [selectedPersonas, setSelectedPersonas] = useState<string[]>([]);
  const [consensusMethod, setConsensusMethod] = useState<string>('');
  const [context, setContext] = useState<Record<string, string>>({});
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!query.trim()) {
      return;
    }

    const submitContext: Record<string, any> = { ...context };
    
    // Add form-specific context
    if (selectedPersonas.length > 0) {
      submitContext.required_personas = selectedPersonas;
    }
    
    if (consensusMethod) {
      submitContext.consensus_method = consensusMethod;
    }

    await onSubmit(query, submitContext);
  };

  const handleContextChange = (key: string, value: string) => {
    setContext(prev => {
      if (!value.trim()) {
        const newContext = { ...prev };
        delete newContext[key];
        return newContext;
      }
      return { ...prev, [key]: value };
    });
  };

  const addContextField = () => {
    const key = `context_${Object.keys(context).length + 1}`;
    setContext(prev => ({ ...prev, [key]: '' }));
  };

  const removeContextField = (key: string) => {
    setContext(prev => {
      const newContext = { ...prev };
      delete newContext[key];
      return newContext;
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Query Input */}
      <div>
        <label htmlFor="query" className="block text-sm font-medium text-gray-700 mb-2">
          Query or Decision to Deliberate
        </label>
        <textarea
          id="query"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Enter your question or describe the decision you need help with..."
          className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
          rows={4}
          required
          disabled={loading}
        />
        <p className="text-sm text-gray-500 mt-1">
          Be specific about what you need help deciding or understanding.
        </p>
      </div>

      {/* Advanced Options Toggle */}
      <div>
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-sm text-blue-600 hover:text-blue-700"
        >
          {showAdvanced ? 'Hide' : 'Show'} Advanced Options
        </button>
      </div>

      {/* Advanced Options */}
      {showAdvanced && (
        <div className="space-y-4 p-4 bg-gray-50 rounded-lg">
          {/* Persona Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Specific Personas (optional)
            </label>
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {personas.map((persona) => (
                <label key={persona.id} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={selectedPersonas.includes(persona.id)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedPersonas(prev => [...prev, persona.id]);
                      } else {
                        setSelectedPersonas(prev => prev.filter(id => id !== persona.id));
                      }
                    }}
                    className="mr-2"
                  />
                  <span className="text-sm">
                    {persona.name} - {persona.expertise_domains.slice(0, 2).join(', ')}
                  </span>
                </label>
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Leave unchecked to use all relevant personas
            </p>
          </div>

          {/* Consensus Method */}
          <div>
            <label htmlFor="consensusMethod" className="block text-sm font-medium text-gray-700 mb-2">
              Consensus Method (optional)
            </label>
            <select
              id="consensusMethod"
              value={consensusMethod}
              onChange={(e) => setConsensusMethod(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Automatic Selection</option>
              <option value="weighted_voting">Weighted Voting</option>
              <option value="majority_rule">Majority Rule</option>
              <option value="unanimous">Unanimous</option>
              <option value="expertise_based">Expertise Based</option>
            </select>
          </div>

          {/* Context Fields */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">
                Additional Context
              </label>
              <button
                type="button"
                onClick={addContextField}
                className="text-sm text-blue-600 hover:text-blue-700"
              >
                + Add Field
              </button>
            </div>
            {Object.entries(context).map(([key, value]) => (
              <div key={key} className="flex gap-2 mb-2">
                <input
                  type="text"
                  placeholder="Field name"
                  value={key.replace('context_', '')}
                  onChange={(e) => {
                    const newKey = e.target.value || key;
                    const newContext = { ...context };
                    delete newContext[key];
                    newContext[newKey] = value;
                    setContext(newContext);
                  }}
                  className="flex-1 p-2 border border-gray-300 rounded text-sm"
                />
                <input
                  type="text"
                  placeholder="Value"
                  value={value}
                  onChange={(e) => handleContextChange(key, e.target.value)}
                  className="flex-2 p-2 border border-gray-300 rounded text-sm"
                />
                <button
                  type="button"
                  onClick={() => removeContextField(key)}
                  className="px-2 py-1 text-red-600 hover:text-red-700"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Submit Button */}
      <div className="flex justify-end">
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {loading && <LoadingSpinner size="sm" />}
          {loading ? 'Deliberating...' : 'Submit for Deliberation'}
        </button>
      </div>
    </form>
  );
}