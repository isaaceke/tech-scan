import {Firestore} from '@google-cloud/firestore';
import {FirestoreStore} from './firestore-store.mjs';
import {createScannerServer} from './http-server.mjs';

// Production uses Cloud Run's service identity (Application Default Credentials).
// Neither a downloaded Google key nor a Microsoft secret belongs in this image.
if (process.env.FIRESTORE_EMULATOR_HOST && process.env.K_SERVICE) throw Error('Production cannot use a Firestore emulator.');
const firestore = new Firestore();
const store = new FirestoreStore(firestore);
const server = createScannerServer({store, env: {...process.env}});
server.listen(Number(process.env.PORT) || 8080, '0.0.0.0', () => process.stdout.write('Scanner service listening.\n'));
process.on('SIGTERM', () => { server.close(); setTimeout(() => process.exit(0), 8000).unref(); });
