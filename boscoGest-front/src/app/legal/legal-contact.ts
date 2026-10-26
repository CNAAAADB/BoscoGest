/**
 * Datos de contacto y titularidad que aparecen en las páginas legales.
 *
 * Centralizados aquí porque los pide Google Play (política de privacidad y
 * página de eliminación de cuenta), los pide Apple, los pide el RGPD y salen
 * repetidos en varias pantallas: cambiarlos debe ser una sola edición.
 */
export const LEGAL = {
  /** Razón social del responsable del tratamiento. */
  organisation:
    'Confederación Nacional de Antiguos Alumnos y Antiguas Alumnas de Don Bosco',
  /** CIF del responsable. */
  taxId: 'G82033069',
  /** Domicilio del responsable. */
  address: 'C/ Alcalá, 211, Oficina 11, 28028 Madrid',
  /**
   * Buzón para ejercer los derechos del RGPD y solicitar la eliminación de la
   * cuenta. Tiene que recibir correo de verdad: las dos tiendas abren la
   * política y comprueban que la dirección exista, y la página de eliminación
   * promete atender la solicitud en 30 días.
   */
  email: 'secretariatecnica@confedebosco.es',
  /** Última revisión del texto legal. */
  lastUpdated: '23 de septiembre de 2026'
} as const;
