import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './assets/css/main.css'
import './assets/css/glass.css'
import App from './App.vue'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.mount('#app')
