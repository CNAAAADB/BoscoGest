Recursos para la ficha de App Store.

screenshots/        Capturas de iPhone 6.9" (1320x2868), simulador de
                    iPhone 17 Pro Max.
screenshots-ipad/   Capturas de iPad 13" (2064x2752), simulador de iPad Pro
                    13". Obligatorias: la app se envia como universal.

Ambas con datos de demostracion inventados.

El icono de la app vive en el propio proyecto Xcode, en
ios/App/App/Assets.xcassets/AppIcon.appiconset/ (1024x1024, sin canal alfa),
y App Store Connect lo toma de ahi al subir el binario: a diferencia de Google
Play, no se sube por separado. Tampoco hay grafico destacado en App Store.

Regenerar las capturas: ver documentation/APP_STORE.md
