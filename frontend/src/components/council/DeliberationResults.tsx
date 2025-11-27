/**
 * Deliberation Results Component
 * Displays the results of a Council deliberation
 */

import React, { useState } from 'react';
import { StatusBadge } from '@/components/ui/StatusBadge';
import type { DeliberationResponse } from '@/types';

interface DeliberationResultsProps {
  deliberation: DeliberationResponse;
}

export function DeliberationResults({ deliberation }: DeliberationResultsProps) {
  const [showDetails, setShowDetails] = useState(false);

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600 bg-green-50';
    if (confidence >= 0.6) return 'text-yellow-600 bg-yellow-50';
    return 'text-red-600 bg-red-50';
  };

  const getAgreementColor = (agreement: number) => {
    if (agreement >= 0.8) return 'text-green-600';
    if (agreement >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    return `${(seconds / 60).toFixed(1)}m`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Query: {deliberation.query}
          </h3>
          <div className="flex items-center gap-4 text-sm text-gray-600">
            <span>ID: {deliberation.id}</span>
            <span>•</span>
            <span>{new Date(deliberation.timestamp).toLocaleString()}</span>
            <span>•</span>
            <span>{formatDuration(deliberation.deliberation_time)}</span>
          </div>
        </div>
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="text-sm text-blue-600 hover:text-blue-700"
        >
          {showDetails ? 'Hide' : 'Show'} Details
        </button>
      </div>

      {/* Decision */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 mt-1">
            <div className="w-2 h-2 bg-blue-600 rounded-full"></div>
          </div>
          <div className="flex-1">
            <h4 className="font-medium text-blue-900 mb-1">Decision</h4>
            <p className="text-blue-800">{deliberation.decision}</p>
          </div>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Confidence */}
        <div className={`p-4 rounded-lg ${getConfidenceColor(deliberation.confidence)}`}>
          <div className="text-2xl font-bold">
            {Math.round(deliberation.confidence * 100)}%
          </div>
          <div className="text-sm font-medium">Confidence</div>
        </div>

        {/* Agreement */}
        <div className="p-4 bg-gray-50 rounded-lg">
          <div className={`text-2xl font-bold ${getAgreementColor(deliberation.agreement_level)}`}>
            {Math.round(deliberation.agreement_level * 100)}%
          </div>
          <div className="text-sm font-medium text-gray-600">Agreement</div>
        </div>

        {/* Personas */}
        <div className="p-4 bg-gray-50 rounded-lg">
          <div className="text-2xl font-bold text-gray-900">
            {deliberation.personas_consulted}
          </div>
          <div className="text-sm font-medium text-gray-600">Personas Consulted</div>
        </div>
      </div>

      {/* Consensus Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Supporting Personas */}
        {deliberation.supporting_personas.length > 0 && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <h4 className="font-medium text-green-900 mb-2">
              Supporting ({deliberation.supporting_personas.length})
            </h4>
            <div className="space-y-1">
              {deliberation.supporting_personas.map((persona) => (
                <div key={persona} className="flex items-center gap-2">
                  <StatusBadge status="running" size="sm" />
                  <span className="text-sm text-green-800">{persona}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Dissenting Personas */}
        {deliberation.dissenting_personas.length > 0 && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <h4 className="font-medium text-red-900 mb-2">
              Dissenting ({deliberation.dissenting_personas.length})
            </h4>
            <div className="space-y-1">
              {deliberation.dissenting_personas.map((persona) => (
                <div key={persona} className="flex items-center gap-2">
                  <StatusBadge status="error" size="sm" />
                  <span className="text-sm text-red-800">{persona}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Alternative Views */}
      {Object.keys(deliberation.alternative_views).length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <h4 className="font-medium text-yellow-900 mb-2">Alternative Perspectives</h4>
          <div className="space-y-2">
            {Object.entries(deliberation.alternative_views).map(([persona, view]) => (
              <div key={persona} className="text-sm">
                <span className="font-medium text-yellow-800">{persona}:</span>{' '}
                <span className="text-yellow-700">{view}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Detailed Information */}
      {showDetails && (
        <div className="space-y-4 pt-4 border-t border-gray-200">
          {/* Consensus Details */}
          <div className="bg-gray-50 rounded-lg p-4">
            <h4 className="font-medium text-gray-900 mb-3">Consensus Process Details</h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-600">Method Used:</span>{' '}
                <span className="font-medium">{deliberation.consensus_details.method_used}</span>
              </div>
              <div>
                <span className="text-gray-600">Reasoning:</span>{' '}
                <span className="font-medium">{deliberation.consensus_details.reasoning || 'N/A'}</span>
              </div>
            </div>
          </div>

          {/* Statistics */}
          {deliberation.statistics && (
            <div className="bg-gray-50 rounded-lg p-4">
              <h4 className="font-medium text-gray-900 mb-3">Deliberation Statistics</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                {Object.entries(deliberation.statistics).map(([key, value]) => (
                  <div key={key}>
                    <div className="text-gray-600">{key.replace(/_/g, ' ')}</div>
                    <div className="font-medium">
                      {typeof value === 'number' ? 
                        (value < 1 ? `${Math.round(value * 100)}%` : value.toFixed(2)) : 
                        String(value)
                      }
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}