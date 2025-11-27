/**
 * Persona Cards Component
 * Displays available personas in the Council of Minds
 */

import React, { useState } from 'react';
import type { PersonaInfo } from '@/types';

interface PersonaCardsProps {
  personas: PersonaInfo[];
}

export function PersonaCards({ personas }: PersonaCardsProps) {
  const [expandedPersona, setExpandedPersona] = useState<string | null>(null);

  const toggleExpanded = (personaId: string) => {
    setExpandedPersona(expandedPersona === personaId ? null : personaId);
  };

  const getPersonaColor = (personaId: string) => {
    // Simple hash function to get consistent colors for personas
    const hash = personaId.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    const colors = [
      'bg-blue-100 text-blue-800 border-blue-200',
      'bg-green-100 text-green-800 border-green-200',
      'bg-purple-100 text-purple-800 border-purple-200',
      'bg-orange-100 text-orange-800 border-orange-200',
      'bg-pink-100 text-pink-800 border-pink-200',
      'bg-indigo-100 text-indigo-800 border-indigo-200',
      'bg-teal-100 text-teal-800 border-teal-200',
      'bg-red-100 text-red-800 border-red-200',
    ];
    return colors[hash % colors.length];
  };

  if (personas.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>No personas are currently available.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {personas.map((persona) => {
        const isExpanded = expandedPersona === persona.id;
        const colorClass = getPersonaColor(persona.id);

        return (
          <div
            key={persona.id}
            className={`border rounded-lg p-4 transition-all cursor-pointer hover:shadow-md ${colorClass}`}
            onClick={() => toggleExpanded(persona.id)}
          >
            {/* Header */}
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <h3 className="font-medium text-sm">{persona.name}</h3>
                <p className="text-xs opacity-80 mt-1 line-clamp-2">
                  {persona.description}
                </p>
              </div>
              <div className="flex-shrink-0 ml-3">
                <svg
                  className={`w-4 h-4 transform transition-transform ${
                    isExpanded ? 'rotate-180' : ''
                  }`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </div>
            </div>

            {/* Expertise Preview */}
            {!isExpanded && (
              <div className="mt-2 flex flex-wrap gap-1">
                {persona.expertise_domains.slice(0, 3).map((domain) => (
                  <span
                    key={domain}
                    className="inline-block px-2 py-1 text-xs rounded-full bg-black bg-opacity-10"
                  >
                    {domain}
                  </span>
                ))}
                {persona.expertise_domains.length > 3 && (
                  <span className="inline-block px-2 py-1 text-xs rounded-full bg-black bg-opacity-10">
                    +{persona.expertise_domains.length - 3} more
                  </span>
                )}
              </div>
            )}

            {/* Expanded Content */}
            {isExpanded && (
              <div className="mt-4 space-y-3 text-sm">
                {/* Full Description */}
                <div>
                  <h4 className="font-medium mb-1">Description</h4>
                  <p className="opacity-80">{persona.description}</p>
                </div>

                {/* Expertise Domains */}
                <div>
                  <h4 className="font-medium mb-2">Expertise Domains</h4>
                  <div className="flex flex-wrap gap-1">
                    {persona.expertise_domains.map((domain) => (
                      <span
                        key={domain}
                        className="inline-block px-2 py-1 text-xs rounded-full bg-black bg-opacity-10"
                      >
                        {domain}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Personality Traits */}
                {persona.personality_traits.length > 0 && (
                  <div>
                    <h4 className="font-medium mb-2">Personality Traits</h4>
                    <div className="flex flex-wrap gap-1">
                      {persona.personality_traits.map((trait) => (
                        <span
                          key={trait}
                          className="inline-block px-2 py-1 text-xs rounded-full bg-black bg-opacity-20"
                        >
                          {trait}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Persona ID for debugging */}
                <div className="pt-2 border-t border-black border-opacity-20">
                  <span className="text-xs opacity-60">ID: {persona.id}</span>
                </div>
              </div>
            )}
          </div>
        );
      })}

      {/* Summary */}
      <div className="text-center text-xs text-gray-500 mt-4">
        {personas.length} persona{personas.length !== 1 ? 's' : ''} available for deliberation
      </div>
    </div>
  );
}