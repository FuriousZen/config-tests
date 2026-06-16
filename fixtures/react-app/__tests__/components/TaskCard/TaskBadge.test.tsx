import { render, screen } from '@testing-library/react';
import React from 'react';
import { describe, expect, it } from 'vitest';
import { TaskBadge } from '../../../app/components/TaskCard/TaskBadge';

describe('TaskBadge', () => {
  it('renders the capitalized priority', () => {
    render(<TaskBadge priority="high" />);
    expect(screen.getByText('High')).toBeTruthy();
  });
});
