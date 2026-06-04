import clsx from 'clsx';
import type React from 'react';

export function Button(
  props: React.ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: 'primary' | 'ghost' | 'danger';
    size?: 'sm' | 'md';
  }
) {
  const { variant = 'primary', size = 'md', className, ...rest } = props;

  const base =
    'inline-flex items-center justify-center rounded-xl font-medium transition shadow-sm disabled:opacity-50 disabled:cursor-not-allowed';
  const sizes = {
    sm: 'h-9 px-3 text-sm',
    md: 'h-11 px-4 text-sm',
  }[size];
  const variants = {
    primary: 'bg-night text-white hover:opacity-95',
    ghost: 'bg-transparent text-night hover:bg-black/5',
    danger: 'bg-red-600 text-white hover:opacity-95',
  }[variant];

  return <button {...rest} className={clsx(base, sizes, variants, className)} />;
}

export function Input(
  props: React.InputHTMLAttributes<HTMLInputElement> & { label?: string }
) {
  const { label, className, ...rest } = props;
  return (
    <label className="block">
      {label ? <div className="mb-1 text-xs text-gray-600">{label}</div> : null}
      <input
        {...rest}
        className={clsx(
          'w-full h-11 rounded-xl border border-gray-200 bg-white px-3 text-sm outline-none focus:ring-2 focus:ring-night/20',
          className
        )}
      />
    </label>
  );
}

export function Textarea(
  props: React.TextareaHTMLAttributes<HTMLTextAreaElement> & { label?: string }
) {
  const { label, className, ...rest } = props;
  return (
    <label className="block">
      {label ? <div className="mb-1 text-xs text-gray-600">{label}</div> : null}
      <textarea
        {...rest}
        className={clsx(
          'w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-night/20',
          className
        )}
      />
    </label>
  );
}

export function Select(
  props: React.SelectHTMLAttributes<HTMLSelectElement> & { label?: string }
) {
  const { label, className, children, ...rest } = props;
  return (
    <label className="block">
      {label ? <div className="mb-1 text-xs text-gray-600">{label}</div> : null}
      <select
        {...rest}
        className={clsx(
          'w-full h-11 rounded-xl border border-gray-200 bg-white px-3 text-sm outline-none focus:ring-2 focus:ring-night/20',
          className
        )}
      >
        {children}
      </select>
    </label>
  );
}

export function Card({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={clsx('rounded-2xl border border-gray-200 bg-white shadow-sm', className)}>
      {children}
    </div>
  );
}
