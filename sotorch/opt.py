import numpy as np
from scipy.optimize import minimize
import torch
from sotorch.grad import jacobian, hessian


class Minimizer:
    def __init__(self, objective):
        '''
        Combination of scipy.optimize.minimize and PyTorch's autograd.

        :param objective: a callable that receives a tensor of parameters and returns a scalar tensor.
                        It should be end-to-end differentiable (e.g. composed of differentiable
                        PyTorch functions).
        '''
        self._obj_tc = objective
        #self.device = device
        #self.dtype = dtype
        self.min_obj = float('inf')

    def _obj_npy(self, x, *args):
        '''
        Auxiliary objective function compatible with NumPy.
        :param x: a tensor.
        :return: the objective value at x to be minimized
        '''
        x = torch.from_numpy(x)
        x = x.requires_grad_(True)
        y = self._obj_tc(x, *args)
        y = y.detach().numpy()
        self.min_obj = min(y, self.min_obj)
        return y
    
    def _jac_npy(self, x, *args):
        '''
        Auxiliary Jacobian function compatible with NumPy.
        :param x: a tensor.
        :return: the Jacobian of the objective function w.r.t x.
        '''
        x = torch.from_numpy(x)
        x = x.requires_grad_(True)
        jac = jacobian(self._obj_tc(x, *args), x)
        jac = jac.detach().numpy()
        return jac
    
    def _hess_npy(self, x, *args):
        '''
        Auxiliary Hessian function compatible with NumPy.
        :param x: a tensor.
        :return: the Hessian of the objective function w.r.t x.
        '''
        x = torch.from_numpy(x)
        x = x.requires_grad_(True)
        hess = hessian(self._obj_tc(x, *args), x)
        hess = hess.detach().numpy()
        return hess

    def minimize(self, x0, **kwargs):
        ''' Performs optimization of objective function.

        :param x0: Initial values for parameters.
        :param kwargs: same as in scipy.optimize.minimize.
        :return: a tuple of three elements containing the answer, success status and optimizer message.
        '''
        args = kwargs['args']
        if 'method' in kwargs:
            method = kwargs['method']
        else:
            method = None
        if 'jac' in kwargs and kwargs['jac'] == None:
            jac = None
        elif method in ['CG', 'BFGS', 'Newton-CG', 'L-BFGS-B',
                        'TNC', 'SLSQP', 'dogleg', 'trust-ncg',
                        'trust-krylov', 'trust-exact', 'trust-constr']:
            jac = self._jac_npy
        else:
            jac = None
        if 'hess' in kwargs and kwargs['hess'] == None:
            hess = None
        elif method in ['Newton-CG', 'dogleg', 'trust-ncg',
                        'trust-krylov', 'trust-exact', 'trust-constr']:
            hess = self._hess_npy
        else:
            hess = None
        if 'hessp' in kwargs:
            raise NotImplementedError('There is no support for \'hessp\' currently.')
        if 'bounds' in kwargs:
            bounds = kwargs['bounds']
        else:
            bounds = None
        if 'options' in kwargs:
            options = kwargs['options']
        else:
            options = None
        if 'constraints' in kwargs:
            constraints = kwargs['constraints']
        else:
            constraints = ()
        if 'tol' in kwargs:
            tol = kwargs['tol']
        else:
            tol = None
        if 'callback' in kwargs:
            callback = kwargs['callback']
        else:
            callback = None

        batchwise = kwargs['batchwise']

        x0 = x0.detach().numpy()
        x0_shape = x0.shape

        suc = []
        msg = []
        self.min_obj = float('inf')
        if batchwise:
            all_res = []
            b = x0.shape[0]

            if method == 'trust-constr':
                x0 = x0.reshape(b, -1)

            if bounds is None:
                bounds = [None] * b
            if args == () or args == [] or args is None:
                args = [None] * b
            if constraints == ():
                constraints = [()] * b
            if tol is None:
                tol = [None] * b

            for i, x0_ in enumerate(x0):
                res = minimize(self._obj_npy,
                               x0_, args=args[i],
                               method=method,
                               jac=jac,
                               hess=hess,
                               bounds=bounds[i],
                               options=options,
                               constraints=constraints[i],
                               tol=tol[i],
                               callback=callback)
                all_res.append(res.x)
                suc.append(res.success)
                msg.append(res.message)
            res = np.array(all_res)
        else:
            if method == 'trust-constr':
                x0 = x0.reshape(-1)

            res = minimize(self._obj_npy,
                           x0, args=args,
                           method=method,
                           jac=jac,
                           hess=hess,
                           bounds=bounds,
                           options=options,
                           constraints=constraints,
                           tol=tol,
                           callback=callback)
            suc.append(res.success)
            msg.append(res.message)
            res = res.x

        ans = res.reshape(x0_shape)
        ans = torch.from_numpy(ans)
        return ans, suc, msg
