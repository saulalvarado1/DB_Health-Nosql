import { expect, test, type Page } from '@playwright/test'

function requiredEnvironment(name: 'E2E_REDIS_URI' | 'E2E_MONGODB_URI'): string {
  const value = process.env[name]
  if (!value) throw new Error(`${name} no está configurada.`)
  return value
}

async function registerInstance(
  page: Page,
  values: { name: string; engine: 'redis' | 'mongodb'; uri: string },
) {
  await page.getByRole('link', { name: 'Bases de datos' }).click()
  await page.getByRole('link', { name: 'Registrar instancia' }).first().click()
  await page.getByLabel('Nombre de la instancia').fill(values.name)
  await page.getByLabel('Motor').selectOption(values.engine)
  await page.getByLabel('URI de conexión').fill(values.uri)
  await page.getByLabel('Intervalo de monitoreo').fill('10')
  await page.getByRole('button', { name: 'Guardar y comenzar monitoreo' }).click()
  await expect(page.getByRole('heading', { name: values.name })).toBeVisible()
}

function monitoredHistory(page: Page) {
  return page
    .getByRole('heading', { name: 'Historial de monitoreo' })
    .locator('xpath=ancestor::section[1]')
}

async function expectAutomaticSample(page: Page, metricCount: number) {
  await expect(monitoredHistory(page).getByText(`${metricCount} valores`).first()).toBeVisible({
    timeout: 35_000,
  })
}

test('recorre el ciclo completo de monitoreo con Redis y MongoDB reales', async ({ page }) => {
  const redisUri = requiredEnvironment('E2E_REDIS_URI')
  const mongodbUri = requiredEnvironment('E2E_MONGODB_URI')
  const suffix = `${Date.now()}-${Math.random().toString(16).slice(2)}`
  const email = `e2e-${suffix}@example.com`
  const password = `E2e-${suffix}-Seguro!`
  const redisName = `Redis E2E ${suffix}`
  const mongodbName = `MongoDB E2E ${suffix}`

  await test.step('registrar la cuenta y comprobar un nuevo inicio de sesión', async () => {
    await page.goto('/access')
    await page.getByRole('tab', { name: 'Crear cuenta' }).click()
    await page.getByLabel('Correo electrónico').fill(email)
    await page.getByLabel('Contraseña').fill(password)
    await page.getByRole('button', { name: 'Registrar cuenta' }).click()
    await expect(page.getByRole('heading', { name: 'Dashboard de salud' })).toBeVisible()

    await page.getByRole('button', { name: 'Cerrar sesión' }).click()
    await expect(page.getByRole('heading', { name: 'Bienvenido nuevamente' })).toBeVisible()
    await page.getByLabel('Correo electrónico').fill(email)
    await page.getByLabel('Contraseña').fill(password)
    await page.getByRole('button', { name: 'Ingresar' }).click()
    await expect(page.getByRole('heading', { name: 'Dashboard de salud' })).toBeVisible()
  })

  await test.step('registrar Redis y validar el worker, historial y catálogo', async () => {
    await registerInstance(page, { name: redisName, engine: 'redis', uri: redisUri })
    await expectAutomaticSample(page, 27)
    await expect(page.getByRole('heading', { name: 'Métricas actuales' })).toBeVisible()

    await page.getByRole('button', { name: 'Recolectar ahora' }).click()
    await expect(page.getByRole('status')).toContainText('27 métricas procesadas')
    await expect(monitoredHistory(page).getByText('27 valores').first()).toBeVisible()
  })

  await test.step('provocar, reconocer y resolver una alerta controlada', async () => {
    await page.getByRole('link', { name: 'Editar umbrales' }).click()
    const memoryRule = page.locator('form.threshold-rule').filter({ hasText: 'Uso de memoria' })
    await memoryRule.getByLabel('Advertencia (percent)').fill('0.01')
    await memoryRule.getByLabel('Crítica (percent)').fill('0.02')
    await memoryRule.getByRole('button', { name: 'Guardar regla' }).click()
    await expect(memoryRule.getByRole('status')).toContainText('Regla guardada')

    await page.getByRole('link', { name: 'Bases de datos' }).click()
    await page.getByRole('link', { name: redisName }).click()
    await page.getByRole('button', { name: 'Recolectar ahora' }).click()
    await expect(page.getByRole('status')).toContainText('27 métricas procesadas')

    await page.getByRole('link', { name: 'Alertas' }).click()
    const activeAlert = page.locator('.alert-card').filter({ hasText: redisName }).first()
    await expect(activeAlert).toContainText('Crítica')
    await activeAlert.getByRole('button', { name: 'Reconocer alerta' }).click()
    await expect(activeAlert).toContainText('Reconocida')

    await page.getByRole('link', { name: 'Umbrales' }).click()
    const restoredMemoryRule = page
      .locator('form.threshold-rule')
      .filter({ hasText: 'Uso de memoria' })
    await restoredMemoryRule.getByLabel('Advertencia (percent)').fill('80')
    await restoredMemoryRule.getByLabel('Crítica (percent)').fill('90')
    await restoredMemoryRule.getByRole('button', { name: 'Guardar regla' }).click()
    await expect(restoredMemoryRule.getByRole('status')).toContainText('Regla guardada')

    await page.getByRole('link', { name: 'Bases de datos' }).click()
    await page.getByRole('link', { name: redisName }).click()
    await page.getByRole('button', { name: 'Recolectar ahora' }).click()
    await expect(page.getByRole('status')).toContainText('27 métricas procesadas')

    await page.getByRole('link', { name: 'Alertas' }).click()
    await page.getByRole('button', { name: 'Resueltas' }).click()
    await expect(page.locator('.alert-card').filter({ hasText: redisName }).first()).toContainText(
      'Resuelta',
    )
  })

  await test.step('registrar MongoDB y validar sus métricas', async () => {
    await registerInstance(page, { name: mongodbName, engine: 'mongodb', uri: mongodbUri })
    await expectAutomaticSample(page, 20)
    await page.getByRole('button', { name: 'Recolectar ahora' }).click()
    await expect(page.getByRole('status')).toContainText('20 métricas procesadas')
    await expect(monitoredHistory(page).getByText('20 valores').first()).toBeVisible()
  })

  await test.step('pausar, reactivar y eliminar las instancias', async () => {
    await page.getByRole('link', { name: 'Bases de datos' }).click()

    const redisRow = page.locator('tr').filter({ hasText: redisName })
    await redisRow.getByRole('button', { name: 'Pausar' }).click()
    await expect(redisRow).toContainText('Pausada')
    await redisRow.getByRole('button', { name: 'Activar' }).click()
    await expect(redisRow).toContainText('Activa')

    page.once('dialog', (dialog) => dialog.accept())
    await redisRow.getByRole('button', { name: 'Eliminar' }).click()
    await expect(redisRow).toHaveCount(0)

    const mongodbRow = page.locator('tr').filter({ hasText: mongodbName })
    page.once('dialog', (dialog) => dialog.accept())
    await mongodbRow.getByRole('button', { name: 'Eliminar' }).click()
    await expect(mongodbRow).toHaveCount(0)
    await expect(page.getByText('No hay bases registradas')).toBeVisible()
  })
})
