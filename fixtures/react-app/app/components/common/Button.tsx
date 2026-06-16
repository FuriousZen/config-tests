import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'ghost' | 'danger';
}

export function Button({ variant = 'primary', className, ...props }: ButtonProps) {
  return <button className={`btn btn-${variant} ${className ?? ''}`.trim()} {...props} />;
}
