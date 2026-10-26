import { MatPaginatorIntl } from '@angular/material/paginator';

/**
 * Spanish labels for every paginator in the application.
 *
 * Angular Material ships its strings in English and there is no locale bundle
 * for them: `MatPaginatorIntl` is the supported way to replace them, and it
 * applies to every `mat-paginator` at once rather than per screen.
 *
 * A placeholder until proper i18n arrives — at which point these strings move
 * into the translation files and this class reads them from there.
 */
export function spanishPaginatorIntl(): MatPaginatorIntl {
  const intl = new MatPaginatorIntl();

  intl.itemsPerPageLabel = 'Elementos por página';
  intl.nextPageLabel = 'Página siguiente';
  intl.previousPageLabel = 'Página anterior';
  intl.firstPageLabel = 'Primera página';
  intl.lastPageLabel = 'Última página';

  /**
   * Material's own wording is "1 – 25 of 300". The range is worth keeping:
   * with three pages of members it is the only clue about where you are.
   */
  intl.getRangeLabel = (page: number, pageSize: number, length: number): string => {
    if (length === 0 || pageSize === 0) {
      return `0 de ${length}`;
    }

    const total = Math.max(length, 0);
    const start = page * pageSize;
    // The last page is usually short, so the end cannot be assumed.
    const end = start < total ? Math.min(start + pageSize, total) : start + pageSize;

    return `${start + 1} – ${end} de ${total}`;
  };

  return intl;
}
