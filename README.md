# Ansible para "Configuration Management"
## 25-05-2016

Ansible es un DSL (domain specific language) escrito en Python que ayuda a configurar servidores, deployar código, manejar servicios, etc. Archivos de Ansible se escriben en YAML, con soporte para templating via Jinja2. No se instala el ejecutable, `ansible-playbook`, en los target machines. Se ejecuta en tu máquina, traduce el YAML a shell commands, y los ejecuta en los target machines a través de SSH.

## Ideas Claves

### Infrastructure as code

#### Porqué?
- Hace 15 años aplicaciones corrían en un sólo servidor que se encargaba de todo. __Configuration management__ no era importante, excepto en empresas grandes
- Hoy todas las empresas tienen servidores especializados: proxy servers, DB, message queue, API...
- Configurar todos de forma homogénea es imposible sin ayuda
- Por eso Ansible, Salt, Puppet, Chef...


#### Beneficios
- __version control__: tu código de Ansible se mete a Git
- __automate deployment desde GitHub__: fácilmente hacer deployment en target machines jalando cualquier branch de un repo de Github
- __control granular__: reiniciar servicios en API servers de staging, hacer deploy a message servers de producción, actualizar env_vars en API servers y message servers...
- __control de todo__: logging, firewalls, cron jobs...
- __comodidad__: no te tienes que conectar via SSH a un servidor tras otro, ejecutando código, pidiéndole a dios que no se te olvide ningún detalle

Tu código de Ansible define toda la configuración de tus servidores. Para tu producto, tu server config es igual de importante como tu application code. Con Ansible tratas este código con el mismo respeto, y lo escribes en un lenguaje mandado a hacer para esto.


### Single source of truth

Con los `group_vars` de Ansible, se definen tus __variables__ en un sólo lugar:

- __env_vars__
  - [group_vars/development.yml](https://github.com/kylebebak/ansible-best-practices/blob/master/resources/development.yml)
- __dependencias/packages__ (del sistema, PyPI, Node...)
  - [group_vars/backend.yml](https://github.com/kylebebak/ansible-best-practices/blob/master/resources/backend.yml)
- rutas (al directorio de tu aplicación, a tu virtualenv, a static files, a log files...)
- ...

Los `group_vars` que se incluyen en un playbook dependen de los `hosts` a los cuales apunta ese playbook.


### DRY

Muchos servidores se agrupan de forma natural:

- __por ambiente__: development vs. staging vs. production
- __por función__: api vs. message vs. database...

Los `inventory` files te permiten apuntar a grupos, y heredar `group_vars` para que éstos no se tienen que definir más de una vez. Ve este ejemplo: [invetories/staging](https://github.com/kylebebak/ansible-best-practices/blob/master/resources/staging)




## Case Studies (Estudios de Caso)

### env_vars

Manejar __env_vars__ puede ser muy doloroso:

- Cómo asegurar que los mismos se deployan a todos los servidores? Combinar y setear tus __env_vars__ en el [Ansible environment keyword](http://docs.ansible.com/ansible/playbooks_environment.html), y hacer un rol que lee éstos, crea un archivo de `.env`, y lo copia al target machine. Así sólo tienes que definir __env_vars__ en tus `group_vars`, y los mismos que usan los playbooks de Ansible estarán en tus servidores.
  - [roles/env_vars/tasks/main.yml](https://github.com/kylebebak/ansible-best-practices/blob/master/resources/main.yml)
  - [roles/env_vars/templates/environment.j2](https://github.com/kylebebak/ansible-best-practices/blob/master/resources/environment.j2)
- Cómo asegurar que están encriptados, para que se puedan meter a version control y así compartirse de forma eficiente con todos los miembros del equipo? Meter __env_vars__ secretos en archivos de __group_vars__ encriptados, usando, por ejemplo, [Ansible Vault](http://docs.ansible.com/ansible/playbooks_vault.html). Sólo tienes que desencriptarlos cuando quieres cambiarlos, o agregar más variables secretos. Puedes usar un Git hook de [pre-commit](https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks) para asegurar que estos los archivos con variables secretos no se pueden meter a version control cuando no están encriptados.
  - [inventories/staging](https://github.com/kylebebak/ansible-best-practices/blob/master/resources/staging)
  - [group_vars/all-secret.template.yml](https://github.com/kylebebak/ansible-best-practices/blob/master/resources/all-secret.template.yml)
  - [group_vars/all-secret.yml](https://github.com/kylebebak/ansible-best-practices/blob/master/resources/all-secret.yml)
  - [hooks/pre-commit](https://github.com/kylebebak/ansible-best-practices/blob/master/resources/pre-commit)
- Cómo hacerlo para que se haga de forma automática, para que nunca pienses en los __env_vars__ otra vez? Definir la ruta a `.env` en el target machine con Ansible, y usar la misma ruta en tus scripts de `upstart` para tus servicios puedan sourcear `.env` cuando corren.
  - [templates/upstart-gunicorn.conf.j2](https://github.com/kylebebak/ansible-best-practices/blob/master/resources/upstart-gunicorn.conf.j2)


### Services (bajo Upstart, con logging)

- [upstart](http://upstart.ubuntu.com/) es un init daemon de Ubuntu, que te permite controlar servicios con un sintaxis hiper-sencillo: `sudo start|stop|restart {name_of_service}`. Nosotros creamos los scripts de upstart con un __role__ de Ansible, que llamamos `upstart`. Aquí es como se invoca este role en nuestro playbook de `message.yml`, que configura nuestros message servers.

~~~yaml
  - role: upstart
    tags: [upstart]
    scripts:
      - "celery-flower"
      - "celery-worker"
      - "celery-beat"
    service_namespace: "-{{ env }}"
    replace_logrotate: true
~~~

- Tenemos varios templates de Ansible que se pasan a este role. [Aquí hay el template](https://github.com/kylebebak/ansible-best-practices/blob/master/resources/upstart-gunicorn.conf.j2) para el script que nos deja controlar a `gunicorn` usando upstart.
- El role convierte los templates en scripts de upstart y los copia a `/etc/init` del target machine, [y también configura logrotate](http://www.linuxcommand.org/man_pages/logrotate8.html).
  - [roles/upstart/templates/upstart-logrotate.j2](https://github.com/kylebebak/ansible-best-practices/blob/master/resources/upstart-logrotate.j2)
- Con este setup, estos servicios se pueden reiniciar por Ansible fácilmente, los logs de todos están en el mismo lugar, `/var/log/upstart/{name_of_service}.log`, y los logs se rotan.


## Demo

Para no tener que memorizar los comandos de `ansible-playbook`, o copiar y pegarlos de un `cookbook` grande, torpe, y sujeto a cambios frecuentes, usamos un programa, [ansible-command-generator.py](https://github.com/kylebebak/ansible-best-practices/blob/master/resources/ansible-command-generator.py), que nos genera los comandos.

Como ejemplo mostraremos un deploy a los servidores de `webapp` y `message` al ambiente de `staging`, especificando el branch que queremos deployar. Después reiniciamos los servicios en estos servidores.

El programa usa una librería de Python que escribí, [questionnaire](https://github.com/kylebebak/questionnaire), para poder definir las preguntas, desplegarlas, y devolver los resultados. __questionnaire__ sirve para cualquier encuesta que quieres armar desde el shell. Funciona en Python 2 y 3, y se puede instalar con `pip install questionnaire`.


## Unas Mejores Prácticas

- Meter funcionalidad reutilizable y modular en `roles`
- Definir `inventories` con herencia de `groups` de servidores. Así tienes control total de cuales `group_vars` se deployan a todos los groups, sin tener definir los `group_vars` más de una vez. [Ve este artículo](http://rosstuck.com/multistage-environments-with-ansible/)
- Crear `playbooks` distintos para servidores con __funciones__ distintos, no __ambientes__ distintos
- Usar `tags` para no tener que correr todo dentro de un role o playbook, sino poder hacer un pick and choose de tasks y roles que quieres correr at runtime
- Manejar servicios y deployment a través de Ansible
- Se creativo. Ansible tiene mucho power y puede tener un gran impacto en tu workflow
- <http://docs.ansible.com/ansible/playbooks_best_practices.html>
