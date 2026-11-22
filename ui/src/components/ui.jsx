const cx = (...parts) => parts.filter(Boolean).join(' ')

export function Button({ variant = 'default', size = 'default', className, as = 'button', ...props }) {
  const Component = as
  return <Component className={cx('ui-button', `ui-button-${variant}`, `ui-button-${size}`, className)} {...props} />
}

export function Card({ className, ...props }) {
  return <section className={cx('ui-card', className)} {...props} />
}

export function CardHeader({ className, ...props }) {
  return <div className={cx('ui-card-header', className)} {...props} />
}

export function CardTitle({ className, ...props }) {
  return <h2 className={cx('ui-card-title', className)} {...props} />
}

export function CardDescription({ className, ...props }) {
  return <p className={cx('ui-card-description', className)} {...props} />
}

export function CardContent({ className, ...props }) {
  return <div className={cx('ui-card-content', className)} {...props} />
}

export function Badge({ variant = 'secondary', className, ...props }) {
  return <span className={cx('ui-badge', `ui-badge-${variant}`, className)} {...props} />
}

export function Select({ className, ...props }) {
  return <select className={cx('ui-select', className)} {...props} />
}

export function Table({ className, ...props }) {
  return <div className="ui-table-container"><table className={cx('ui-table', className)} {...props} /></div>
}

export function TableHeader({ className, ...props }) {
  return <thead className={cx('ui-table-header', className)} {...props} />
}

export function TableBody({ className, ...props }) {
  return <tbody className={cx('ui-table-body', className)} {...props} />
}

export function TableRow({ className, ...props }) {
  return <tr className={cx('ui-table-row', className)} {...props} />
}

export function TableHead({ className, ...props }) {
  return <th className={cx('ui-table-head', className)} {...props} />
}

export function TableCell({ className, ...props }) {
  return <td className={cx('ui-table-cell', className)} {...props} />
}

