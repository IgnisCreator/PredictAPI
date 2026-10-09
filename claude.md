Instrucciones para el agente de IA en este proyecto. Léelas completas antes de escribir código. Si una instrucción del usuario contradice este archivo, gana el usuario, pero avísale del conflicto.
1. Contexto del proyecto
Aplicación web construida sin escribir código a mano. El usuario dirige, tú construyes.
Stack React 18+ con Vite, Tailwind CSS 3+, JavaScript (no TypeScript salvo que el usuario lo pida).
Backend Supabase (base de datos Postgres, autenticación, almacenamiento de archivos). No se construye un servidor propio.
Despliegue Vercel. Cada push a GitHub genera un despliegue. La rama main es producción; cualquier otra rama genera una URL de preview.
Fuente de verdad la URL de Vercel, no localhost. El servidor local sirve solo para iterar rápido antes de hacer push. Nada se da por terminado hasta que funciona en la URL de preview o producción.
El usuario puede no ser programador. Explica cada decisión técnica en 1 o 2 frases en español simple antes de ejecutarla.
2. Idioma y comunicación
Responde siempre en español.
Todo el texto visible de la interfaz (botones, títulos, mensajes de error, estados vacíos) va en español, salvo que el usuario indique otro idioma.
Los nombres de archivos, componentes, variables, funciones, tablas y columnas van en inglés, siguiendo la convención estándar de React y de SQL (snake_case en la base de datos, camelCase en JavaScript).
Nunca uses jerga sin explicarla la primera vez. Ejemplo Voy a crear un componente (una pieza reutilizable de la interfaz) llamado Navbar.
3. Configuración inicial
Cuando el proyecto parte de cero, sigue este orden y no saltes pasos
3.1 Proyecto React
npm create vite@latest nombre-proyecto -- --template react
cd nombre-proyecto
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install @supabasesupabase-js
Configura tailwind.config.js con content [.index.html, .src.{js,jsx}].
Agrega las 3 directivas de Tailwind a srcindex.css.
3.2 Supabase
Pide al usuario que cree el proyecto en supabase.com y te entregue 2 valores desde Settings  API la URL del proyecto y la clave anon public. Nunca pidas ni uses la clave service_role.
Crea .env.local en la raíz con
VITE_SUPABASE_URL=httpsxxxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...
Agrega .env.local y .env a .gitignore en el mismo paso.
Crea srclibsupabase.js con el cliente único
import { createClient } from @supabasesupabase-js;

export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY
);
Todo acceso a datos pasa por este cliente. No crees un segundo createClient en ningún otro archivo.
3.3 Git y GitHub
git init, primer commit, y crea el repositorio en GitHub (público o privado según indique el usuario).
Verifica que .env.local no aparezca en git status antes del primer push.
3.4 Vercel
Pide al usuario que importe el repositorio en vercel.com (Add New  Project). Vercel detecta Vite solo; no cambies el comando de build ni la carpeta de salida (dist).
Indícale que agregue las 2 variables de entorno (VITE_SUPABASE_URL y VITE_SUPABASE_ANON_KEY) en Settings  Environment Variables, marcadas para Production, Preview y Development.
Crea vercel.json en la raíz para que las rutas del frontend no den 404 al recargar
{
  rewrites [{ source (.), destination index.html }]
}
Confirma con el usuario que la URL de producción carga antes de construir nada más. Ese es el punto de partida verificado.
4. Estructura de archivos
src
  components     Componentes reutilizables (Button.jsx, Card.jsx, Navbar.jsx)
  pages          Vistas completas (Home.jsx, About.jsx)
  assets         Imágenes, íconos, fuentes locales
  hooks          Hooks personalizados (useUser.js, useTasks.js)
  lib            supabase.js y utilidades compartidas
  services       Funciones que leen y escriben en Supabase (tasks.js, profiles.js)
  data           Datos de ejemplo solo mientras la tabla real no exista
  App.jsx         Composición principal
  index.css       Tailwind y estilos base
supabase
  migrations     Archivos SQL numerados con la creación de tablas y políticas
vercel.json
.env.local        Nunca se sube al repositorio
Un componente por archivo. Nombre del archivo igual al nombre del componente.
Componentes de menos de 150 líneas. Si crece más, divídelo.
Los componentes no llaman a Supabase directamente. Llaman a una función de srcservices. Así, si cambia una tabla, se corrige en 1 archivo.
No instales librerías de componentes (shadcn, MUI, Chakra, DaisyUI) salvo que el usuario lo pida. El diseño se construye con Tailwind puro. Esa es la razón principal por la que el resultado no se ve genérico.
5. Sistema de diseño reglas duras
Esta sección es la más importante del archivo. El objetivo es que la interfaz parezca diseñada por un estudio, no generada por una plantilla.
5.1 Antes de escribir código
Antes de construir cualquier pantalla, define y muestra al usuario un mini sistema de diseño
Paleta 4 a 6 colores con hex, cada uno con nombre y función (fondo, texto, acento, borde, superficie).
Tipografía 2 fuentes con roles claros. Una display con carácter para títulos, una de lectura para el cuerpo. Cárgalas desde Google Fonts en index.html.
Concepto de layout 1 frase que describa la estructura de la página.
Elemento firma el único detalle memorable de esta interfaz (un tratamiento tipográfico, una interacción, una forma de mostrar los datos). Uno solo.
Espera la aprobación del usuario antes de construir. Si el usuario dice hazlo tú, decide y explica por qué.
5.2 Prohibiciones (esto es lo que delata a la IA)
Prohibido el gradiente violeta a azul, el violeta a rosado y cualquier gradiente como protagonista del hero.
Prohibida la combinación fondo crema + serif de alto contraste + acento terracota. Es el cliché número 1 de diseño generado por IA en 2025 y 2026.
Prohibido el fondo casi negro con un solo acento verde ácido o naranja neón, salvo que el rubro lo justifique y el usuario lo apruebe.
Prohibido usar Inter, Roboto o la fuente por defecto del sistema para los títulos. Para el cuerpo, Inter se permite solo si la display tiene carácter propio.
Prohibidos los emojis como íconos de la interfaz. Usa SVG (Lucide o Heroicons como paquete de íconos está permitido).
Prohibido el texto de relleno tipo Lorem ipsum o Potencia tu negocio con soluciones innovadoras. Todo el copy debe ser concreto y específico al proyecto. Si falta información, pregunta al usuario qué hace el producto y para quién.
Prohibidas las tarjetas con sombra genérica, borde redondeado xl y un ícono centrado arriba, repetidas 3 veces en una grilla. Si necesitas mostrar 3 características, busca otra estructura lista numerada con jerarquía, filas alternadas, tabla editorial.
Prohibido animar todo. Máximo 1 momento de movimiento orquestado por página (una entrada, un hover con intención). Respeta prefers-reduced-motion.
Prohibidos los badges tipo ✨ Nuevo o 🚀 Impulsado por IA en el hero.
5.3 Obligaciones
Escala tipográfica definida y consistente define tamaños en el config de Tailwind o usa una escala fija (por ejemplo 14, 16, 20, 28, 40, 64) y no te salgas de ella.
Espaciado con ritmo múltiplos de 4 u 8. El aire entre secciones comunica jerarquía.
Contraste AA mínimo entre texto y fondo. Verifica los grises sobre fondos de color.
Estados completos en todo elemento interactivo hover, focus visible, disabled, loading cuando aplique.
Toda pantalla que lee de Supabase tiene 3 estados diseñados cargando, vacío (sin datos todavía) y error (la consulta falló). No muestres una pantalla en blanco mientras llegan los datos.
Responsive real diseña mobile primero, verifica en 375px, 768px y 1280px.
Los botones dicen exactamente lo que hacen Guardar cambios, no Enviar. Voz activa en todo el copy.
El hero abre con lo más característico del producto, no con una frase genérica. Si el producto muestra datos, muestra datos reales o realistas desde el primer pantallazo.
5.4 Autocrítica obligatoria
Después de construir cada pantalla, revisa contra esta lista y corrige antes de mostrar
¿Podría esta pantalla pertenecer a cualquier otro producto Si sí, falta especificidad.
¿Hay más de 1 elemento compitiendo por ser el protagonista Quita uno.
¿El copy podría haberlo escrito una plantilla Reescríbelo con el contenido real del proyecto.
¿Usé alguna de las prohibiciones de 5.2 Corrígelo sin que el usuario lo pida.
6. Convenciones de código
Componentes funcionales con hooks. Nada de clases.
Props desestructuradas en la firma del componente.
Clases de Tailwind directamente en el JSX. No crees archivos CSS adicionales salvo para animaciones con keyframes.
Estado local con useState. Estado compartido con props o context. La sesión del usuario vive en un AuthContext que envuelve App.jsx. No instales Redux ni Zustand salvo pedido explícito.
Toda llamada a Supabase va en srcservices y devuelve { data, error }. El componente decide qué mostrar en cada caso; nunca ignores error.
Datos de ejemplo en srcdata solo mientras la tabla no exista en Supabase. Cuando la tabla existe, el archivo de ejemplo se borra en el mismo commit. Nunca hardcodees datos dentro del JSX.
Sin console.log en el código final.
Comenta solo lo que no es obvio, en español.
7. Flujo de trabajo
Entiende el pedido. Si es ambiguo, haz máximo 2 preguntas antes de construir.
Propón el plan en 3 a 5 pasos y el sistema de diseño (sección 5.1). Si el pedido necesita datos, incluye en el plan qué tablas se crean y quién puede leer y escribir en cada una.
Construye por partes primero la tabla y sus políticas en Supabase, luego la estructura, luego el estilo, luego las interacciones.
Después de cada parte, haz commit y push, y entrega al usuario la URL de preview de Vercel indicando qué revisar y qué debería ver.
Si algo falla, lee el error completo (consola del navegador, logs de build en Vercel o logs de Supabase) antes de intentar arreglos. Explica la causa en 1 frase.
Nunca borres trabajo existente para empezar de nuevo sin confirmación del usuario.
8. Qué no hacer
No agregues funcionalidades que el usuario no pidió.
No cambies el stack (no migres a Next.js, no agregues TypeScript, no cambies Tailwind por CSS modules, no reemplaces Supabase por otro backend) por iniciativa propia.
No toques archivos de configuración que ya funcionan salvo necesidad concreta.
No generes más de 1 pantalla por iteración sin aprobación.
No uses datos personales reales en los ejemplos ni en las tablas de prueba.
No crees tablas sin políticas de seguridad (sección 11.2). Una tabla abierta es un error, no un atajo.
9. Control de versiones y despliegue
git init al crear el proyecto y primer commit apenas el proyecto compile. Push a GitHub antes de construir la primera pantalla.
Un commit por cada funcionalidad que quede operativa, con mensaje descriptivo en español Agrega navbar responsive, no cambios.
Trabaja en ramas por funcionalidad (featurelogin, featuretabla-tareas). Cada rama genera su URL de preview en Vercel; ahí revisa el usuario. Cuando aprueba, se fusiona a main y Vercel publica a producción.
Antes de una modificación grande o riesgosa, haz commit y push del estado actual. Es la red de seguridad del usuario.
Nunca ejecutes git push --force, nunca borres la carpeta .git y nunca hagas git reset --hard sin confirmación explícita del usuario.
Si el usuario quiere volver atrás, muéstrale los últimos 5 commits con git log --oneline -5 y explícale a cuál conviene volver y por qué. En Vercel también puede hacer Promote to Production sobre un despliegue anterior desde el panel; explícale esa opción como la más rápida.
10. Cuando algo falla y no sale
Máximo 3 intentos para el mismo error. Si al tercer intento persiste, detente, resume qué probaste y qué sospechas, y pide al usuario el error completo consola del navegador, pantalla del build fallido en Vercel o el mensaje de Supabase.
Si funciona en local y falla en Vercel, lo primero que se revisa son las variables de entorno en el panel de Vercel. Es la causa en 9 de cada 10 casos.
Si una consulta devuelve una lista vacía sin error, sospecha de las políticas RLS antes que del código. Revísalas en Supabase  Authentication  Policies.
No reescribas un archivo completo para arreglar un bug puntual. Localiza la causa y haz el cambio mínimo.
Si el error viene de una dependencia, verifica la versión instalada en package.json antes de asumir la sintaxis de la documentación.
Nunca declares algo arreglado sin verificarlo en la URL de Vercel. Indica al usuario exactamente qué debería ver para confirmar.
11. Datos, autenticación y claves
11.1 Tablas
Cada tabla se crea con un archivo SQL en supabasemigrations numerado (001_create_tasks.sql). El usuario lo pega en Supabase  SQL Editor y ejecuta. Muéstrale el SQL y explícale en 1 frase qué crea.
Toda tabla lleva id uuid primary key default gen_random_uuid(), created_at timestamptz default now() y, si pertenece a un usuario, user_id uuid references auth.users(id) on delete cascade.
Nombres en inglés y snake_case tasks, due_date, is_done.
11.2 Seguridad (RLS)
Activa Row Level Security en cada tabla en el mismo SQL que la crea. Sin excepción.
Política por defecto un usuario solo lee, crea, edita y borra sus propias filas (auth.uid() = user_id). Si una tabla debe ser pública de lectura, el usuario lo aprueba por escrito y la política lo dice explícitamente.
La clave anon es pública por diseño y puede vivir en el frontend. La que protege los datos es RLS, no la clave. La clave service_role nunca se usa en este proyecto.
11.3 Autenticación
Usa Supabase Auth. Empieza con email y contraseña salvo que el usuario pida otro proveedor.
Configura en Supabase  Authentication  URL Configuration la URL de producción de Vercel como Site URL, y agrega https.vercel.app a las Redirect URLs para que los previews también funcionen.
La sesión se lee con supabase.auth.getSession() al cargar y se escucha con onAuthStateChange. Las páginas privadas redirigen a login si no hay sesión.
11.4 Archivos
Imágenes subidas por usuarios van a Supabase Storage, en un bucket con políticas propias. Nunca a srcassets.
11.5 Claves y variables de entorno
Las claves viven en .env.local (local) y en el panel de Vercel (preview y producción). En ningún otro lugar.
Prohibido escribir una clave dentro de un archivo .js, .jsx o .json del repositorio.
Si el usuario necesita integrar un servicio cuya clave debe permanecer secreta (por ejemplo un proveedor de pagos o de IA), explícale que el frontend expone todo, y que eso se resuelve con una Edge Function de Supabase. Propónlo como paso aparte; no lo construyas sin aprobación.
12. Rutas y navegación
Si la aplicación tiene 1 sola vista, no instales router. Usa estado para alternar secciones si hace falta.
Con 2 o más páginas, instala react-router-dom y define las rutas en App.jsx. El vercel.json de la sección 3.4 es obligatorio para que las rutas carguen al recargar o al abrir un enlace directo.
Toda página nueva necesita entrada en el router, enlace visible en la navegación y un título propio en la pestaña del navegador.
Las páginas que requieren sesión se envuelven en un componente ProtectedRoute que redirige a login.
13. Imágenes e íconos
Íconos lucide-react, importados individualmente. Nunca emojis, nunca SVG pegados a mano si existe el ícono en la librería.
Imágenes de relleno usa servicios de placeholder realistas (por ejemplo picsum.photos) o pide al usuario sus imágenes reales. Nada de cajas grises con la palabra imagen.
Toda imagen lleva atributo alt descriptivo en español.
Imágenes estáticas del sitio van en srcassets y se importan. Imágenes que sube el usuario van a Supabase Storage (sección 11.4).
14. Trabajo con specs (Kiro)
Para funcionalidades de más de 1 pantalla, con lógica no trivial o que crean tablas nuevas, usa el modo spec en vez de vibe coding directo
requirements.md qué necesita el usuario, en criterios verificables.
design.md cómo se va a construir, componentes, tablas, políticas RLS y flujo de datos.
tasks.md pasos ordenados, cada uno completable y verificable por separado.
Ejecuta las tareas de a una y marca el avance. No saltes al paso 5 si el 2 no está verificado.
Si durante la implementación descubres que el diseño estaba mal, actualiza el spec primero y luego el código, para que el documento nunca mienta.
Cambios chicos (ajustar un color, corregir un texto) no necesitan spec. Criterio si el cambio toca 3 o más archivos o crea una tabla, va con spec.
15. Checklist de entrega por pantalla
Antes de dar una pantalla por terminada, verifica los 10 puntos. Si alguno falla, corrige antes de mostrar
El build de Vercel termina sin errores y la URL de preview carga sin errores ni warnings en la consola del navegador.
Se ve bien en 375px, 768px y 1280px.
Todo elemento interactivo tiene hover y focus visible.
Los estados cargando, vacío y error existen y se ven bien.
El copy es real y específico del proyecto, sin relleno.
Pasó la autocrítica de la sección 5.4.
Las imágenes tienen alt y los íconos vienen de lucide-react.
Cada tabla nueva tiene RLS activo y sus políticas probadas con 2 usuarios distintos (uno no ve los datos del otro).
No hay claves en el repositorio y las variables de entorno están cargadas en Vercel.
Hay un commit en GitHub con el estado funcionando y el usuario tiene la URL para revisarlo.
